"""Xonsh shell variant for the Jupyter kernel.

``ipykernel.iostream.OutStream`` (installed by ``IPKernelApp.init_io``) takes
care of capturing stdout/stderr — including subprocess output via ``dup2`` —
and routes it to the iopub channel. Therefore the shell only needs to be a
thin :class:`xonsh.shells.base_shell.BaseShell` subclass.
"""

from xonsh.shells.base_shell import BaseShell


class JupyterShell(BaseShell):
    """Pass-through xonsh shell. All stream capture is done by ipykernel."""


__all__ = ("JupyterShell",)
