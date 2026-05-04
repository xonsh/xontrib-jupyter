"""Shared pytest fixtures for the xonsh-jupyter integration tests.

Each integration test boots a real kernel subprocess via
``jupyter_client.start_new_kernel`` and talks to it over ZMQ.  To avoid
clobbering the developer's user-level Jupyter kernelspec, the
``xonsh_kernelspec`` session-scoped fixture installs the spec into a
temporary prefix and points ``$JUPYTER_DATA_DIR`` at it for the duration
of the session.  Any pre-existing user spec is left untouched.
"""

from __future__ import annotations

import contextlib
import os
import time
from typing import Any

import pytest

# All integration tests require a working jupyter_client + a freshly
# installed kernelspec — skip the whole suite cleanly on platforms or
# environments where that bootstrap fails (e.g. minimal sdists in CI
# without Jupyter installed).
jupyter_client = pytest.importorskip("jupyter_client")
KernelSpecManager = pytest.importorskip("jupyter_client.kernelspec").KernelSpecManager
start_new_kernel = jupyter_client.manager.start_new_kernel


def _install_xonsh_kernelspec(prefix: str) -> None:
    """Install the in-tree kernelspec into ``prefix/share/jupyter``.

    Uses the package's own installer (``xonsh_jupyter.alias.jupyter_kernel``)
    so the installed spec stays in lock-step with whatever the package
    would put on a real user's machine.
    """
    from xonsh_jupyter.alias import jupyter_kernel

    jupyter_kernel(prefix=prefix)


@pytest.fixture(scope="session")
def xonsh_kernelspec(tmp_path_factory) -> str:
    """Install the kernelspec into an isolated prefix for the test session."""
    prefix = str(tmp_path_factory.mktemp("xonshk-prefix"))
    _install_xonsh_kernelspec(prefix)

    data_dir = os.path.join(prefix, "share", "jupyter")
    saved = os.environ.get("JUPYTER_DATA_DIR")
    # ``start_new_kernel`` reads kernelspecs via ``KernelSpecManager``,
    # which honours ``$JUPYTER_DATA_DIR``.  Prepend our prefix so it
    # wins over any user-level install.
    os.environ["JUPYTER_DATA_DIR"] = data_dir

    # Sanity check — fail fast if the spec did not land where expected.
    ksm = KernelSpecManager()
    if "xonsh" not in ksm.find_kernel_specs():
        pytest.skip(
            f"xonsh kernelspec not found after installing into {prefix!r}; "
            "check xonsh_jupyter.alias.jupyter_kernel"
        )

    yield prefix

    if saved is None:
        os.environ.pop("JUPYTER_DATA_DIR", None)
    else:
        os.environ["JUPYTER_DATA_DIR"] = saved


@pytest.fixture
def kernel(xonsh_kernelspec):
    """Start a fresh kernel for the test, shut it down at teardown.

    Yields a ``(KernelManager, KernelClient)`` pair.  The kernel is fully
    isolated: a new subprocess every test, so state from one test cannot
    leak into the next (important for ``test_interrupt`` which depends on
    a clean ``XSH`` singleton).
    """
    km, kc = start_new_kernel(kernel_name="xonsh")
    try:
        yield km, kc
    finally:
        # Best-effort teardown — the kernel may already be dead from the
        # test (e.g. a SIGKILL in test_interrupt).
        with contextlib.suppress(Exception):
            km.shutdown_kernel(now=True)


def run_cell(
    kc,
    code: str,
    *,
    timeout: float = 10.0,
    msg_types: tuple[str, ...] = (
        "stream",
        "execute_result",
        "display_data",
        "update_display_data",
        "error",
        "comm_open",
        "comm_msg",
        "comm_close",
    ),
) -> tuple[str, list[tuple[str, dict[str, Any]]]]:
    """Execute ``code`` and return ``(reply_status, iopub_messages)``.

    ``iopub_messages`` is filtered to ``msg_types`` of interest and is
    ordered by arrival.  Status messages and irrelevant chatter are
    dropped.  Returns once the matching ``execute_reply`` lands on the
    shell channel.
    """
    msg_id = kc.execute(code)
    deadline = time.time() + timeout
    iopub: list[tuple[str, dict[str, Any]]] = []
    reply_status = "TIMEOUT"

    while time.time() < deadline:
        # Drain iopub for our msg_id
        try:
            r = kc.get_iopub_msg(timeout=0.2)
        except Exception:
            r = None
        if r is not None and r["parent_header"].get("msg_id") == msg_id:
            t = r["msg_type"]
            if t in msg_types:
                iopub.append((t, r["content"]))
        # Check shell for the reply
        try:
            sm = kc.get_shell_msg(timeout=0.0)
        except Exception:
            sm = None
        if sm is not None and sm["parent_header"].get("msg_id") == msg_id:
            reply_status = sm["content"].get("status", "?")
            # Drain any remaining iopub for this msg_id
            drain_until = time.time() + 0.5
            while time.time() < drain_until:
                try:
                    r = kc.get_iopub_msg(timeout=0.1)
                except Exception:
                    break
                if r["parent_header"].get("msg_id") == msg_id:
                    t = r["msg_type"]
                    if t in msg_types:
                        iopub.append((t, r["content"]))
                    if t == "status" and r["content"]["execution_state"] == "idle":
                        return reply_status, iopub
            return reply_status, iopub

    return reply_status, iopub


def find_first(
    iopub: list[tuple[str, dict[str, Any]]], msg_type: str
) -> dict[str, Any] | None:
    """Return the content of the first ``msg_type`` message, or ``None``."""
    for t, c in iopub:
        if t == msg_type:
            return c
    return None


def find_all(
    iopub: list[tuple[str, dict[str, Any]]], msg_type: str
) -> list[dict[str, Any]]:
    """Return contents of every ``msg_type`` message in order."""
    return [c for t, c in iopub if t == msg_type]


# Re-export helpers so test files can ``from conftest import ...``.
__all__ = ("find_all", "find_first", "kernel", "run_cell", "xonsh_kernelspec")
