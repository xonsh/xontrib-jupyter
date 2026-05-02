"""Xonsh Jupyter kernel built on top of ``ipykernel.ipkernel.IPythonKernel``.

Inheriting from ``IPythonKernel`` (rather than the bare ``Kernel`` base)
gives us a fully-wired ``ZMQInteractiveShell`` for free: rich
``execute_result`` / ``display_data`` MIME bundles via IPython's
``DisplayFormatter``, working ``IPython.display.display(...)``, ipywidgets
through the global comm-manager, the ``pre_execute`` / ``post_execute``
event bus that ``matplotlib_inline`` hooks into, and per-cell parent-header
propagation through the shell's stdout/stderr/displayhook/display_pub.

This module only implements the xonsh-specific bits: bootstrap the xonsh
session inside the kernel process, route ``do_execute`` through xonsh's
execer instead of IPython's ``run_cell``, and provide xonsh-aware
``do_complete`` / ``do_is_complete`` / ``do_inspect`` / ``do_shutdown``.
"""

from __future__ import annotations

import contextlib
import inspect as _inspect
import sys
import traceback as _tb
from typing import Any

from ipykernel.ipkernel import IPythonKernel
from xonsh import __version__ as xonsh_version
from xonsh.built_ins import XSH
from xonsh.commands_cache import predict_true
from xonsh.completer import Completer
from xonsh.main import setup as xonsh_setup

from xonsh_jupyter.shell import JupyterShell


def _short_version(v: str) -> str:
    return ".".join(v.split(".")[:3])


class XonshKernel(IPythonKernel):
    """Jupyter kernel for the xonsh shell."""

    implementation = "xonsh"
    implementation_version = xonsh_version
    banner = "Xonsh is a full-featured and cross-platform Python-powered shell."

    # Both fields override traitlets defined on Kernel via traitlets, so they
    # are intentionally instance-shaped rather than ClassVar.
    language_info = {  # noqa: RUF012
        "name": "xonsh",
        "version": _short_version(xonsh_version),
        "mimetype": "text/x-xonsh",
        "file_extension": ".xsh",
        # ``xonsh`` Pygments lexer assumes the xonsh runtime is loaded in
        # the current process (it dereferences ``XSH.aliases`` while
        # tokenizing) and crashes in clients like ``jupyter console``.
        # ``bash`` is universally available and gives sensible highlighting.
        # TODO: switch to ``"xonsh"`` once xonsh >= 0.23.4 is on PyPI
        # (https://github.com/xonsh/xonsh/pull/6384 fixed the crash).
        "pygments_lexer": "bash",
        "codemirror_mode": {"name": "shell"},
    }

    help_links = [  # noqa: RUF012
        {"text": "Xonsh tutorial", "url": "https://xon.sh/tutorial.html"},
        {"text": "Xonsh xontribs", "url": "https://xon.sh/xontribs.html"},
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._init_xonsh_session()
        self.completer = Completer()
        # Route ``sys.displayhook`` to the shell's ZMQShellDisplayHook so
        # top-level expressions (``2+2`` on its own line) go through
        # IPython's ``DisplayFormatter`` and get rich MIME bundles
        # (``text/html`` for DataFrames, ``image/png`` for matplotlib
        # figures, ``text/markdown`` for ``IPython.display.Markdown``,
        # etc.) instead of bare ``text/plain: repr(value)``.  IPython's
        # ``run_cell`` does this swap per cell; since we bypass
        # ``run_cell``, we set it once at startup.
        sys.displayhook = self.shell.displayhook
        # Inject ``get_ipython`` into the xonsh namespace so cells can use
        # the standard IPython entry point (``get_ipython()``) without an
        # extra ``from IPython import get_ipython`` import.  IPython's
        # InteractiveShell normally puts this in the user_ns; xonsh has
        # its own namespace, so we mirror it explicitly.
        if XSH.shell is not None and XSH.shell.ctx is not None:
            XSH.shell.ctx["get_ipython"] = lambda: self.shell

    def _init_xonsh_session(self) -> None:
        """Bootstrap the xonsh session inside the kernel process."""
        if XSH.builtins is not None:
            return
        # Subprocess output is captured by ipykernel's ``OutStream(watchfd=True)``
        # which dups FD 1/2 onto a pipe and publishes bytes to iopub — this
        # gives live streaming for long-running commands like ``tail -f``.
        # Empty PROMPT/RIGHT_PROMPT/BOTTOM_TOOLBAR/TITLE prevent xonsh from
        # printing prompt strings into cell output.
        xonsh_setup(
            shell_type=JupyterShell,
            env={
                "PAGER": "cat",
                "PROMPT": "",
                "RIGHT_PROMPT": "",
                "BOTTOM_TOOLBAR": "",
                "TITLE": "",
            },
            aliases={"less": "cat"},
            xontribs=["coreutils"],
            threadable_predictors={"git": predict_true, "man": predict_true},
        )
        cc = XSH.commands_cache
        if cc is not None and cc.is_only_functional_alias("cat"):
            XSH.aliases["cat"] = "xonsh-cat"
            XSH.env["PAGER"] = "xonsh-cat"

    # ------------------------------------------------------------------ execute

    async def do_execute(  # type: ignore[override]
        self,
        code: str,
        silent: bool,
        store_history: bool = True,
        user_expressions: dict | None = None,
        allow_stdin: bool = False,
        *,
        cell_meta: dict | None = None,
        cell_id: str | None = None,
    ) -> dict:
        if not code.strip():
            return {
                "status": "ok",
                "execution_count": self.execution_count,
                "payload": [],
                "user_expressions": {},
            }

        # IPythonKernel.set_parent → ZMQInteractiveShell.set_parent already
        # propagates the parent header to displayhook, display_pub, stdout
        # and stderr.  Fire ``pre_execute`` so any registered hook (e.g.
        # ``matplotlib_inline.configure_inline_support``) can prepare for
        # the new cell.
        from IPython.core.interactiveshell import ExecutionInfo, ExecutionResult

        info = ExecutionInfo(
            raw_cell=code,
            store_history=store_history,
            silent=silent,
            shell_futures=False,
            cell_id=cell_id,
            transformed_cell=code,
        )
        result = ExecutionResult(info)
        result.execution_count = self.execution_count

        self.shell.events.trigger("pre_execute")
        if not silent:
            self.shell.events.trigger("pre_run_cell", info)

        shell = XSH.shell
        history = XSH.history
        try:
            try:
                shell.default(code)
            except KeyboardInterrupt as exc:
                result.error_in_exec = exc
                self._kill_orphaned_children()
                return {
                    "status": "error",
                    "execution_count": self.execution_count,
                    "ename": "KeyboardInterrupt",
                    "evalue": "interrupted",
                    "traceback": [],
                }
            except BaseException as exc:
                # Never let user code crash the kernel — surface every
                # exception, including SystemExit, as an error reply.
                result.error_in_exec = exc
                self._kill_orphaned_children()
                return self._publish_exception(exc, silent=silent)

            rtn = 0
            if history is not None and len(history) > 0:
                rtn = history.rtns[-1] or 0
            if rtn:
                result.error_in_exec = RuntimeError(f"NonZeroExitStatus: {rtn}")
                content = {
                    "status": "error",
                    "execution_count": self.execution_count,
                    "ename": "NonZeroExitStatus",
                    "evalue": str(rtn),
                    "traceback": [f"Process exited with non-zero status: {rtn}"],
                }
                if not silent:
                    self.send_response(self.iopub_socket, "error", content)
                return content

            return {
                "status": "ok",
                "execution_count": self.execution_count,
                "payload": [],
                "user_expressions": {},
            }
        finally:
            # ``post_execute`` is the hook ``matplotlib_inline`` uses to
            # flush pending figures into the cell.  ``post_run_cell`` is
            # invoked by libraries that want the cell's
            # ``ExecutionResult`` (e.g. autoreload).  Trigger both so
            # nothing is silently dropped because we bypassed
            # ``shell.run_cell``.
            self.shell.events.trigger("post_execute")
            if not silent:
                self.shell.events.trigger("post_run_cell", result)

    def _kill_orphaned_children(self) -> None:
        """Terminate any child processes that survived an interrupt.

        xonsh installs its own SIGINT handler (which kills the foreground
        subprocess group) only for commands routed through ``PopenThread``
        — i.e. captured/threadable commands.  Uncaptured runs of
        unthreadable binaries — e.g. ``tail -f`` started without
        ``$XONSH_CAPTURE_ALWAYS`` — go through ``subprocess.Popen``
        directly, so SIGINT raises ``KeyboardInterrupt`` in this thread
        without touching the child.  The cell would then look "done" while
        the subprocess kept running orphaned in the kernel.  Reap them
        explicitly here so an interrupt always means "everything stops".
        """
        try:
            import psutil
        except ImportError:
            return
        try:
            children = psutil.Process().children(recursive=True)
        except psutil.Error:
            return
        for child in children:
            with contextlib.suppress(psutil.Error):
                child.terminate()
        _, alive = psutil.wait_procs(children, timeout=0.5)
        for child in alive:
            with contextlib.suppress(psutil.Error):
                child.kill()

    def _publish_exception(self, exc: BaseException, silent: bool = False) -> dict:
        tb_lines = _tb.format_exception(type(exc), exc, exc.__traceback__)
        content = {
            "status": "error",
            "execution_count": self.execution_count,
            "ename": type(exc).__name__,
            "evalue": str(exc),
            "traceback": tb_lines,
        }
        if not silent:
            self.send_response(self.iopub_socket, "error", content)
        return content

    # ----------------------------------------------------------------- complete

    def do_complete(self, code: str, cursor_pos: int) -> dict:
        line_start = code.rfind("\n", 0, cursor_pos) + 1
        line_stop = code.find("\n", cursor_pos)
        if line_stop == -1:
            line_stop = len(code)
        else:
            line_stop += 1
        line = code[line_start:line_stop]
        endidx = cursor_pos - line_start
        line_ex: str = XSH.aliases.expand_alias(line, endidx)

        last_space = line[:endidx].rfind(" ")
        begidx = last_space + 1 if last_space >= 0 else 0
        prefix = line[begidx:endidx]
        expand_offset = len(line_ex) - len(line)

        multiline_text = code
        cursor_index = cursor_pos
        if line != line_ex:
            multiline_text = code[:line_start] + line_ex + code[line_stop:]
            cursor_index += expand_offset

        ctx = XSH.shell.ctx if XSH.shell is not None else None

        rtn, _ = self.completer.complete(
            prefix,
            line_ex,
            begidx + expand_offset,
            endidx + expand_offset,
            ctx,
            multiline_text=multiline_text,
            cursor_index=cursor_index,
        )
        matches = sorted(rtn) if rtn else []
        return {
            "status": "ok",
            "matches": matches,
            "cursor_start": begidx,
            "cursor_end": endidx,
            "metadata": {},
        }

    # -------------------------------------------------------------- is_complete

    def do_is_complete(self, code: str) -> dict:
        if not code.strip():
            return {"status": "complete", "indent": ""}
        execer = XSH.execer
        if execer is None:
            return {"status": "unknown", "indent": ""}
        try:
            execer.parse(code, ctx=set(), mode="exec")
        except SyntaxError as exc:
            msg = (str(exc) or "").lower()
            incomplete_markers = (
                "eof",
                "unexpected end",
                "unterminated",
                "expected indented block",
                "incomplete",
            )
            if any(m in msg for m in incomplete_markers):
                return {"status": "incomplete", "indent": ""}
            return {"status": "invalid"}
        except Exception:
            return {"status": "unknown", "indent": ""}
        return {"status": "complete", "indent": ""}

    # ----------------------------------------------------------------- inspect

    def do_inspect(  # type: ignore[override]
        self,
        code: str,
        cursor_pos: int,
        detail_level: int = 0,
        omit_sections: Any = (),
    ) -> dict:
        word = _word_under_cursor(code, cursor_pos)
        text = _xonsh_inspect(word, detail_level)
        if not text:
            return {"status": "ok", "found": False, "data": {}, "metadata": {}}
        return {
            "status": "ok",
            "found": True,
            "data": {"text/plain": text},
            "metadata": {},
        }

    # ---------------------------------------------------------------- shutdown

    def do_shutdown(self, restart: bool) -> dict:  # type: ignore[override]
        with contextlib.suppress(Exception):
            XSH.unload()
        return super().do_shutdown(restart)


# ----------------------------------------------------------------------- helpers


def _word_under_cursor(code: str, pos: int) -> str:
    if pos > len(code):
        pos = len(code)
    left = pos
    while left > 0 and (code[left - 1].isalnum() or code[left - 1] in "_."):
        left -= 1
    right = pos
    while right < len(code) and (code[right].isalnum() or code[right] in "_."):
        right += 1
    return code[left:right]


def _xonsh_inspect(word: str, detail_level: int) -> str | None:
    if not word:
        return None
    shell = XSH.shell
    ctx = shell.ctx if shell is not None and shell.ctx is not None else {}
    obj = ctx.get(word)
    if obj is not None:
        doc = _inspect.getdoc(obj) or repr(obj)
        if detail_level >= 1:
            try:
                src = _inspect.getsource(obj)
            except (OSError, TypeError):
                src = None
            if src:
                return f"{doc}\n\n--- source ---\n{src}"
        return doc
    aliases = XSH.aliases
    if aliases is not None and word in aliases:
        return f"alias: {word!r} -> {aliases[word]!r}"
    return None


# -------------------------------------------------------------------------- main


def main() -> None:
    """Entry point for ``python -m xonsh_jupyter.kernel``."""
    from ipykernel.kernelapp import IPKernelApp

    IPKernelApp.launch_instance(kernel_class=XonshKernel)


if __name__ == "__main__":
    main()
