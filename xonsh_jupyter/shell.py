"""Xonsh shell variant for the Jupyter kernel.

``ipykernel.iostream.OutStream`` (installed by ``IPKernelApp.init_io``) takes
care of capturing stdout/stderr and routes it to the iopub channel.
``JupyterShell`` only suppresses terminal-control escape sequences that the
base shell would otherwise emit and that JupyterLab cannot interpret.
"""

from xonsh.shells.base_shell import BaseShell


class JupyterShell(BaseShell):
    """Pass-through xonsh shell with terminal-control output suppressed."""

    def settitle(self):
        # BaseShell.settitle() emits ``\x1b]0;<title>\x07`` directly to
        # ``sys.stdout`` before every command, which leaks into notebook
        # cells as garbage. JupyterLab is not a terminal — drop the escape.
        return


__all__ = ("JupyterShell",)
