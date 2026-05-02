import sys
from inspect import signature
from unittest.mock import MagicMock

import pytest
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


def _stub_ipykernel(monkeypatch):
    """Provide a class-shaped stub for ``ipykernel.kernelbase.Kernel``.

    ``MagicMock`` instances cannot be used as base classes; we need real
    Python ``type`` s so that ``class XonshKernel(IPythonKernel)``
    succeeds at import time without pulling in the full ipykernel /
    IPython / zmq stack.
    """
    fake_base_cls = type("FakeKernelBase", (), {})
    fake_ipy_kernel_cls = type("FakeIPyKernel", (fake_base_cls,), {})
    kernelbase = MagicMock(Kernel=fake_base_cls)
    ipkernel = MagicMock(IPythonKernel=fake_ipy_kernel_cls)
    kernelapp = MagicMock()
    pkg = MagicMock(kernelbase=kernelbase, ipkernel=ipkernel, kernelapp=kernelapp)
    monkeypatch.setitem(sys.modules, "ipykernel", pkg)
    monkeypatch.setitem(sys.modules, "ipykernel.kernelbase", kernelbase)
    monkeypatch.setitem(sys.modules, "ipykernel.ipkernel", ipkernel)
    monkeypatch.setitem(sys.modules, "ipykernel.kernelapp", kernelapp)


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    global XonshKernel
    if XonshKernel is None:
        _stub_ipykernel(monkeypatch)
        from xonsh_jupyter import kernel

        XonshKernel = kernel.XonshKernel


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

    xession.aliases["gb"] = "git branch"
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


def test_do_is_complete_handles_complete_input(xession):
    kernel = MagicMock()
    result = XonshKernel.do_is_complete(kernel, "echo hello")
    assert result["status"] in {"complete", "unknown"}


def test_do_is_complete_empty_string(xession):
    kernel = MagicMock()
    result = XonshKernel.do_is_complete(kernel, "")
    assert result == {"status": "complete", "indent": ""}
