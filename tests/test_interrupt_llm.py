"""Integration tests for cell interruption.

Two regressions are guarded:

1. ``tail -f`` (an unthreadable subprocess that blocks indefinitely)
   must die when the user presses *Stop*.  The historical bug: xonsh
   only installs its own SIGINT handler when a command goes through
   ``PopenThread`` (i.e. captured / threadable runs).  Uncaptured
   ``tail -f`` went straight to ``subprocess.Popen``, the SIGINT
   raised ``KeyboardInterrupt`` in the kernel thread, ``do_execute``
   returned, but the child kept running orphaned.

2. The fix in ``XonshKernel._kill_orphaned_children`` reaps any
   children that survived the interrupt.  These tests assert the kernel
   has zero descendants shortly after we send the interrupt — both with
   ``XONSH_CAPTURE_ALWAYS=True`` (PopenThread path; xonsh's own SIGINT
   handler does the killing) and ``=False`` (orphan-cleanup path).
"""

from __future__ import annotations

import sys
import time

import pytest

if sys.platform == "win32":
    pytest.skip(
        "POSIX-only: relies on SIGINT semantics + psutil.Process.children",
        allow_module_level=True,
    )

psutil = pytest.importorskip("psutil")

from .conftest import run_cell  # noqa: E402


def _kernel_pid(km) -> int:
    return km.provisioner.pid


def _live_children(pid: int) -> list[int]:
    try:
        return [c.pid for c in psutil.Process(pid).children(recursive=True)]
    except psutil.NoSuchProcess:
        return []


def _wait_no_children(pid: int, *, timeout: float = 3.0) -> list[int]:
    """Poll up to ``timeout`` seconds; return the final children list."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        kids = _live_children(pid)
        if not kids:
            return []
        time.sleep(0.05)
    return _live_children(pid)


@pytest.fixture
def tmp_target(tmp_path):
    """A small file ``tail`` can follow."""
    path = tmp_path / "interrupt-target.log"
    path.write_text("")
    return str(path)


def _execute_async_then_interrupt(km, kc, code: str, *, dwell: float = 1.5) -> str:
    """Submit ``code``, sleep for ``dwell`` so the subprocess starts,
    then issue the interrupt.  Returns the resulting reply status.
    """
    msg_id = kc.execute(code)
    time.sleep(dwell)
    km.interrupt_kernel()

    deadline = time.time() + 10.0
    while time.time() < deadline:
        try:
            r = kc.get_shell_msg(timeout=1.0)
        except Exception:
            continue
        if r["parent_header"].get("msg_id") == msg_id:
            return r["content"].get("status", "?")
    return "TIMEOUT"


# Each parametrised case is a self-contained reproduction of a real
# blocking-subprocess scenario.  All must end with no surviving kernel
# descendants — that's the invariant ``_kill_orphaned_children`` defends.
INTERRUPT_KILL_CASES = [
    pytest.param(
        "tail -f {target}",
        True,  # needs target file
        id="tail-f-single",
    ),
    pytest.param(
        "sleep 30",
        False,
        id="sleep-30",
    ),
    pytest.param(
        "tail -f {target} | cat",
        True,
        id="tail-f-pipeline",
    ),
]


@pytest.mark.parametrize("template, needs_target", INTERRUPT_KILL_CASES)
def test_interrupt_kills_subprocess(kernel, tmp_target, template, needs_target):
    km, kc = kernel
    pid = _kernel_pid(km)
    code = template.format(target=tmp_target) if needs_target else template

    status = _execute_async_then_interrupt(km, kc, code)
    assert status in {"error", "ok"}, status
    assert _wait_no_children(pid) == [], (
        f"subprocess survived interrupt; kernel children still alive: "
        f"{_live_children(pid)}"
    )


def test_interrupt_works_with_capture_always_disabled(kernel, tmp_target):
    """Repro for the historical bug: without ``XONSH_CAPTURE_ALWAYS``
    the subprocess is uncaptured and bypasses xonsh's own SIGINT path.
    The kernel's ``_kill_orphaned_children`` cleanup must catch it.
    """
    km, kc = kernel
    pid = _kernel_pid(km)

    status, _ = run_cell(kc, "$XONSH_CAPTURE_ALWAYS = False")
    assert status == "ok"

    status = _execute_async_then_interrupt(km, kc, f"tail -f {tmp_target}")
    assert status in {"error", "ok"}
    assert _wait_no_children(pid) == [], (
        f"tail -f orphaned after interrupt with CAPTURE_ALWAYS=False: "
        f"{_live_children(pid)}"
    )


def test_interrupt_python_loop(kernel):
    km, kc = kernel
    status = _execute_async_then_interrupt(
        km, kc, "import time\nfor _ in range(60):\n    time.sleep(1)"
    )
    assert status == "error"


def test_kernel_still_responsive_after_interrupt(kernel, tmp_target):
    """Interrupt must not damage the kernel — a follow-up cell should
    execute normally.
    """
    km, kc = kernel
    _execute_async_then_interrupt(km, kc, f"tail -f {tmp_target}")

    status, iopub = run_cell(kc, "print('alive')")
    assert status == "ok"
    streams = [c for t, c in iopub if t == "stream"]
    assert any("alive" in s["text"] for s in streams)
