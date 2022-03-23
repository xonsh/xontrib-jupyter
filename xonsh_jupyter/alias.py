XONSH_JUPYTER_KERNEL = "xonsh"


def jupyter_kernel(
    user=False,
    prefix=None,
    root=None,
):
    """Generate xonsh kernel for jupyter.

    Parameters
    ----------
    user : -u, --user
        Install kernel spec in user config directory.
    prefix : -p, --prefix
        Installation prefix for bin, lib, etc.
    root : -r, --root
        Install relative to this alternate root directory.
    """
    import json
    import os
    import sys
    import tempfile

    try:
        from jupyter_client.kernelspec import KernelSpecManager, NoSuchKernel
    except ImportError as e:
        raise ImportError("Jupyter not found in current Python environment") from e

    ksm = KernelSpecManager()

    prefix = prefix or sys.prefix
    spec = {
        "argv": [
            sys.executable,
            "-m",
            "xonsh_jupyter.kernel",
            "-f",
            "{connection_file}",
        ],
        "display_name": "Xonsh",
        "language": "xonsh",
        "codemirror_mode": "shell",
    }

    if root and prefix:
        # os.path.join isn't used since prefix is probably absolute
        prefix = root + prefix

    try:
        old_jup_kernel = ksm.get_kernel_spec(XONSH_JUPYTER_KERNEL)
        if not old_jup_kernel.resource_dir.startswith(prefix):
            print(
                "Removing existing Jupyter kernel found at {}".format(
                    old_jup_kernel.resource_dir
                )
            )
        ksm.remove_kernel_spec(XONSH_JUPYTER_KERNEL)
    except NoSuchKernel:
        pass

    if sys.platform == "win32":
        # Ensure that conda-build detects the hard coded prefix
        spec["argv"][0] = spec["argv"][0].replace(os.sep, os.altsep)
        prefix = prefix.replace(os.sep, os.altsep)

    with tempfile.TemporaryDirectory() as d:
        os.chmod(d, 0o755)  # Starts off as 700, not user readable
        with open(os.path.join(d, "kernel.json"), "w") as f:
            json.dump(spec, f, sort_keys=True)

        print("Installing Jupyter kernel spec:")
        print(f"  root: {root!r}")
        if user:
            print(f"  as user: {user}")
        elif root and prefix:
            print(f"  combined prefix {prefix!r}")
        else:
            print(f"  prefix: {prefix!r}")
        ksm.install_kernel_spec(
            d, XONSH_JUPYTER_KERNEL, user=user, prefix=(None if user else prefix)
        )
        return 0
