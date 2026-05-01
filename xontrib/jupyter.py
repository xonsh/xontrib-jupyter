from xonsh.built_ins import XSH
from xonsh.xonfig import xonfig_main

from xonsh_jupyter.alias import jupyter_kernel

__all__ = ()

_LOADED_FLAG = "_xonsh_jupyter_xontrib_registered"

if not getattr(xonfig_main, _LOADED_FLAG, False):
    xonfig_main.add_command(jupyter_kernel)
    setattr(xonfig_main, _LOADED_FLAG, True)

    @XSH.builtins.events.on_xonfig_info_requested
    def jupyter_info(**kwargs):
        jup_ksm = jup_kernel = None
        try:
            from jupyter_client.kernelspec import KernelSpecManager

            jup_ksm = KernelSpecManager()
            jup_kernel = jup_ksm.find_kernel_specs().get("xonsh")
        except Exception:
            pass
        return [("jupyter", jup_ksm is not None), ("jupyter kernel", jup_kernel)]
