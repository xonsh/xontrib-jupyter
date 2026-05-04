"""Integration tests for rich display in the xonsh kernel.

Verify that ``execute_result`` and ``display_data`` IOPub messages carry
the MIME bundles produced by IPython's ``DisplayFormatter``: HTML for
``IPython.display.HTML(...)`` and objects with ``_repr_html_``, markdown
for ``Markdown(...)``, plain text for everything else.  These rely on
``XonshKernel`` inheriting ``IPythonKernel`` and routing
``sys.displayhook`` to ``shell.displayhook`` (rather than the bare
``ZMQDisplayHook`` ``IPKernelApp`` installs by default).
"""

from __future__ import annotations

import time

import pytest

from .conftest import find_all, find_first, run_cell

# ---------------------------------------------------------------- execute_result

EXECUTE_RESULT_CASES = [
    pytest.param("2 + 2", "text/plain", "4", id="int-text"),
    pytest.param("'hello'", "text/plain", "'hello'", id="str-text"),
    pytest.param(
        "from IPython.display import HTML\nHTML('<b>bold</b>')",
        "text/html",
        "<b>bold</b>",
        id="HTML-rich",
    ),
    pytest.param(
        "from IPython.display import Markdown\nMarkdown('# Title')",
        "text/markdown",
        "# Title",
        id="Markdown-rich",
    ),
    pytest.param(
        "class Foo:\n"
        "    def _repr_html_(self): return '<table><tr><td>fancy</td></tr></table>'\n"
        "Foo()",
        "text/html",
        "fancy",
        id="custom-_repr_html_",
    ),
]


@pytest.mark.parametrize("code, mime, expected", EXECUTE_RESULT_CASES)
def test_execute_result_mime_bundle(kernel, code, mime, expected):
    _, kc = kernel
    status, iopub = run_cell(kc, code)
    assert status == "ok"
    res = find_first(iopub, "execute_result")
    assert res is not None, "expected execute_result for top-level expression"
    assert mime in res["data"], (
        f"expected {mime} in MIME bundle, got keys: {list(res['data'])}"
    )
    assert expected in res["data"][mime]
    # text/plain is always present as fallback even for rich types
    assert "text/plain" in res["data"]


def test_pandas_dataframe_renders_as_html(kernel):
    pytest.importorskip("pandas")
    _, kc = kernel
    status, iopub = run_cell(
        kc,
        "import pandas as pd\npd.DataFrame({'x': [1, 2, 3]})",
    )
    assert status == "ok"
    res = find_first(iopub, "execute_result")
    assert res is not None
    # pandas registers a ``text/html`` formatter that emits a ``<table>``.
    html = res["data"].get("text/html", "")
    assert "<table" in html


# ------------------------------------------------------------------ display_data


def test_display_data_via_display_function(kernel):
    _, kc = kernel
    status, iopub = run_cell(
        kc,
        "from IPython.display import display, HTML\n"
        "display(HTML('<i>via display</i>'))\n"
        "None",
    )
    assert status == "ok"
    dd = find_first(iopub, "display_data")
    assert dd is not None, "display() should publish display_data, not stream"
    assert "<i>via display</i>" in dd["data"].get("text/html", "")


def test_display_does_not_emit_execute_result(kernel):
    """Last expression is ``None``, so no execute_result expected — only
    the display_data published by ``display()``.
    """
    _, kc = kernel
    status, iopub = run_cell(
        kc,
        "from IPython.display import display, HTML\ndisplay(HTML('<x/>'))\nNone",
    )
    assert status == "ok"
    assert find_first(iopub, "execute_result") is None


# ----------------------------------------------------------------------- streams


def test_print_still_streams_to_stdout(kernel):
    _, kc = kernel
    status, iopub = run_cell(kc, "print('plain stdout')")
    assert status == "ok"
    streams = find_all(iopub, "stream")
    assert any(s["name"] == "stdout" and "plain stdout" in s["text"] for s in streams)


# ---------------------------------------------------------- xonsh integration


def test_get_ipython_is_injected_into_xonsh_namespace(kernel):
    """``get_ipython()`` must work without an explicit
    ``from IPython import get_ipython`` — the kernel mirrors IPython's
    convention by injecting it into ``XSH.shell.ctx`` at startup.
    """
    _, kc = kernel
    status, iopub = run_cell(
        kc,
        "shell = get_ipython()\nprint(type(shell).__name__)",
    )
    assert status == "ok"
    streams = find_all(iopub, "stream")
    text = "".join(s["text"] for s in streams)
    assert "InteractiveShell" in text  # ZMQInteractiveShell is a subclass


def test_parent_header_propagates_to_execute_result(kernel):
    """Every IOPub message must carry the originating cell's ``msg_id``
    in ``parent_header``, otherwise JupyterLab cannot associate output
    with a cell and renders nothing.
    """
    _, kc = kernel
    msg_id = kc.execute("42")
    deadline = time.time() + 5.0
    while time.time() < deadline:
        try:
            r = kc.get_iopub_msg(timeout=0.5)
        except Exception:
            continue
        if r["msg_type"] == "execute_result":
            assert r["parent_header"].get("msg_id") == msg_id
            assert r["content"]["data"]["text/plain"] == "42"
            return
    pytest.fail("execute_result for last expression never arrived within 5s")
