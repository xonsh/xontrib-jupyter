"""Integration tests for ipywidgets in the xonsh kernel.

The kernel inherits ``IPythonKernel``, which registers a global
``comm.CommManager`` and wires ``shell_handlers`` for ``comm_open`` /
``comm_msg`` / ``comm_close``.  ipywidgets uses that machinery to talk
to its frontend counterpart over the IOPub channel, so a working setup
must:

  - emit at least one ``comm_open`` message with target ``jupyter.widget``
    when a widget is constructed,
  - publish ``application/vnd.jupyter.widget-view+json`` as the MIME
    bundle of an ``execute_result`` (or ``display_data``) so JupyterLab
    knows to render the widget instead of its plain-text fallback.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "ipywidgets",
    reason="ipywidgets is an optional dependency; tests skipped when absent",
)

from .conftest import find_all, find_first, run_cell

WIDGET_VIEW_MIME = "application/vnd.jupyter.widget-view+json"


# Build the slider once per test (each gets a fresh kernel) and parametrise
# over the two ways a widget reaches the frontend: as the cell's last
# expression (→ execute_result) or via an explicit ``display(...)`` call
# (→ display_data).  Both must wrap the widget in the same MIME bundle.

WIDGET_PUBLISH_CASES = [
    pytest.param(
        "from ipywidgets import IntSlider\nIntSlider(value=42)",
        "execute_result",
        id="last-expression",
    ),
    pytest.param(
        "from ipywidgets import IntSlider\n"
        "from IPython.display import display\n"
        "display(IntSlider(value=7))\n",
        "display_data",
        id="display-call",
    ),
]


@pytest.mark.parametrize("code, msg_type", WIDGET_PUBLISH_CASES)
def test_widget_published_with_widget_view_mime(kernel, code, msg_type):
    _, kc = kernel
    status, iopub = run_cell(kc, code)
    assert status == "ok"

    msg = find_first(iopub, msg_type)
    assert msg is not None, f"expected a {msg_type} message"
    assert WIDGET_VIEW_MIME in msg["data"], (
        f"expected {WIDGET_VIEW_MIME} in {msg_type} data, got keys: {list(msg['data'])}"
    )
    assert msg["data"][WIDGET_VIEW_MIME].get("model_id")


def test_widget_construction_emits_comm_open(kernel):
    _, kc = kernel
    status, iopub = run_cell(
        kc,
        "from ipywidgets import IntSlider\nIntSlider(value=42)",
    )
    assert status == "ok"
    comm_opens = find_all(iopub, "comm_open")
    assert comm_opens, "ipywidgets should open at least one comm channel"
    targets = {c.get("target_name") for c in comm_opens}
    assert "jupyter.widget" in targets


def test_value_change_triggers_comm_msg_update(kernel):
    """Mutating a synced trait must send a ``comm_msg`` with
    ``method=update`` so the frontend mirrors the new value.
    """
    _, kc = kernel
    status, _ = run_cell(
        kc,
        "from ipywidgets import IntSlider\ns = IntSlider(value=0, min=0, max=10)\ns",
    )
    assert status == "ok"

    status, iopub = run_cell(kc, "s.value = 7")
    assert status == "ok"
    comm_msgs = find_all(iopub, "comm_msg")
    methods = [c.get("data", {}).get("method") for c in comm_msgs]
    assert "update" in methods, (
        f"expected 'update' comm_msg after setting value, got: {methods}"
    )


def test_observe_callback_runs_on_value_change(kernel):
    """The widget machinery should wire ``traitlets.observe`` callbacks
    to value mutations even without a frontend in the loop.
    """
    _, kc = kernel
    status, iopub = run_cell(
        kc,
        "from ipywidgets import IntSlider\n"
        "s = IntSlider(value=0, min=0, max=10)\n"
        "events = []\n"
        "s.observe(lambda c: events.append(c['new']), names='value')\n"
        "s.value = 5\n"
        "s.value = 7\n"
        "print(events)",
    )
    assert status == "ok"
    streams = find_all(iopub, "stream")
    text = "".join(s["text"] for s in streams)
    assert "[5, 7]" in text, f"expected observer to fire twice, output was: {text!r}"
