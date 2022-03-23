import sys
from inspect import signature
from unittest.mock import MagicMock

import pytest
from xonsh.aliases import Aliases
from xonsh.completer import Completer

XonshKernel = None

EXPANSION_CASES = (
    (
        "sanity",
        6,
        dict(
            prefix="sanity",
            line="sanity",
            begidx=0,
            endidx=6,
            multiline_text="sanity",
            cursor_index=6,
        ),
    ),
    (
        "gb ",
        3,
        dict(
            prefix="",
            line="git branch ",
            begidx=11,
            endidx=11,
            multiline_text="git branch ",
            cursor_index=11,
        ),
    ),
    (
        "gb ",
        1,
        dict(
            prefix="g",
            line="gb ",
            begidx=0,
            endidx=1,
            multiline_text="gb ",
            cursor_index=1,
        ),
    ),
    (
        "gb",
        0,
        dict(
            prefix="",
            line="gb",
            begidx=0,
            endidx=0,
            multiline_text="gb",
            cursor_index=0,
        ),
    ),
    (
        " gb ",
        0,
        dict(
            prefix="",
            line=" gb ",  # the PTK completer `lstrip`s the line
            begidx=0,
            endidx=0,
            multiline_text=" gb ",
            cursor_index=0,
        ),
    ),
    (
        "gb --",
        5,
        dict(
            prefix="--",
            line="git branch --",
            begidx=11,
            endidx=13,
            multiline_text="git branch --",
            cursor_index=13,
        ),
    ),
    (
        "nice\ngb --",
        10,
        dict(
            prefix="--",
            line="git branch --",
            begidx=11,
            endidx=13,
            multiline_text="nice\ngit branch --",
            cursor_index=18,
        ),
    ),
    (
        "nice\n gb --",
        11,
        dict(
            prefix="--",
            line=" git branch --",
            begidx=12,
            endidx=14,
            multiline_text="nice\n git branch --",
            cursor_index=19,
        ),
    ),
    (
        "gb -- wow",
        5,
        dict(
            prefix="--",
            line="git branch -- wow",
            begidx=11,
            endidx=13,
            multiline_text="git branch -- wow",
            cursor_index=13,
        ),
    ),
    (
        "gb --wow",
        5,
        dict(
            prefix="--",
            line="git branch --wow",
            begidx=11,
            endidx=13,
            multiline_text="git branch --wow",
            cursor_index=13,
        ),
    ),
)


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    global XonshKernel
    if XonshKernel is None:
        monkeypatch.setitem(sys.modules, "zmq", MagicMock())
        monkeypatch.setitem(sys.modules, "zmq.eventloop", MagicMock())
        monkeypatch.setitem(sys.modules, "zmq.error", MagicMock())
        import xonsh.jupyter_kernel

        XonshKernel = xonsh.jupyter_kernel.XonshKernel


@pytest.mark.parametrize("code, index, expected_args", EXPANSION_CASES)
def test_completion_alias_expansion(
    code,
    index,
    expected_args,
    monkeypatch,
    xession,
):
    xonsh_completer_mock = MagicMock(spec=Completer)
    xonsh_completer_mock.complete.return_value = set(), 0

    kernel = MagicMock()
    kernel.completer = xonsh_completer_mock

    monkeypatch.setattr(xession, "aliases", Aliases(gb=["git branch"]))
    monkeypatch.setattr(xession.shell, "ctx", None, raising=False)

    XonshKernel.do_complete(kernel, code, index)
    mock_call = xonsh_completer_mock.complete.call_args
    args, kwargs = mock_call
    expected_args["self"] = None
    expected_args["ctx"] = None
    assert (
        signature(Completer.complete).bind(None, *args, **kwargs).arguments
        == expected_args
    )
