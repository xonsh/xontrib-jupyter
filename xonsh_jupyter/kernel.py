"""Xonsh Jupyter kernel built on top of ``ipykernel.kernelbase.Kernel``.

The kernel inherits the wire transport, HMAC signing, heartbeat, busy/idle
bracketing, parent-header propagation, ``interrupt_request`` handling, and
``OutStream``-based subprocess capture from ipykernel. This module only
implements the xonsh-specific bits: ``do_execute``, ``do_complete``,
``do_is_complete``, ``do_inspect`` and ``do_shutdown``.
"""

from __future__ import annotations

import inspect as _inspect
import traceback as _tb
from typing import Any, ClassVar

from ipykernel.kernelbase import Kernel
from xonsh import __version__ as xonsh_version
from xonsh.built_ins import XSH
from xonsh.commands_cache import predict_true
from xonsh.completer import Completer
from xonsh.main import setup as xonsh_setup

from xonsh_jupyter.shell import JupyterShell


def _short_version(v: str) -> str:
    return ".".join(v.split(".")[:3])


class XonshKernel(Kernel):
    """Jupyter kernel for the xonsh shell."""

    implementation = "xonsh"
    implementation_version = xonsh_version
    banner = "Xonsh — Python-powered, cross-platform shell"

    language_info: ClassVar = {
        "name": "xonsh",
        "version": _short_version(xonsh_version),
        "mimetype": "text/x-sh",
        "file_extension": ".xsh",
        "pygments_lexer": "xonsh",
        "codemirror_mode": {"name": "shell"},
    }

    help_links: ClassVar = [
        {"text": "Xonsh tutorial", "url": "https://xon.sh/tutorial.html"},
        {"text": "Xonsh xontribs", "url": "https://xon.sh/xontribs.html"},
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._init_xonsh_session()
        self.completer = Completer()

    def _init_xonsh_session(self) -> None:
        """Bootstrap the xonsh session inside the kernel process."""
        if XSH.builtins is not None:
            return
        xonsh_setup(
            shell_type=JupyterShell,
            env={"PAGER": "cat"},
            aliases={"less": "cat"},
            xontribs=["coreutils"],
            threadable_predictors={"git": predict_true, "man": predict_true},
        )
        cc = XSH.commands_cache
        if cc is not None and cc.is_only_functional_alias("cat"):
            XSH.aliases["cat"] = "xonsh-cat"
            XSH.env["PAGER"] = "xonsh-cat"

    # ------------------------------------------------------------------ execute

    def do_execute(
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

        shell = XSH.shell
        history = XSH.history
        try:
            shell.default(code)
        except KeyboardInterrupt:
            return {
                "status": "error",
                "execution_count": self.execution_count,
                "ename": "KeyboardInterrupt",
                "evalue": "interrupted",
                "traceback": [],
            }
        except BaseException as exc:  # noqa: BLE001 — never let user code crash the kernel
            return self._publish_exception(exc, silent=silent)

        rtn = 0
        if history is not None and len(history) > 0:
            rtn = history.rtns[-1] or 0
        if rtn:
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
        except Exception:  # noqa: BLE001
            return {"status": "unknown", "indent": ""}
        return {"status": "complete", "indent": ""}

    # ----------------------------------------------------------------- inspect

    def do_inspect(
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

    def do_shutdown(self, restart: bool) -> dict:
        try:
            XSH.unload()
        except Exception:  # noqa: BLE001
            pass
        return {"status": "ok", "restart": restart}


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
