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
    import shutil
    import sys
    import tempfile
    from pathlib import Path

    from .resources import RESOURCES_DIR

    try:
        from jupyter_client.kernelspec import KernelSpecManager, NoSuchKernel
    except ImportError as e:
        raise ImportError("Jupyter not found in current Python environment") from e

    ksm = KernelSpecManager()

    prefix = prefix or sys.prefix
    if root and prefix:
        # `os.path.join` would discard `root` because `prefix` is absolute, so
        # the original chrooted-install behaviour is preserved by concatenation.
        prefix = root + prefix

    try:
        old_jup_kernel = ksm.get_kernel_spec(XONSH_JUPYTER_KERNEL)
        if not old_jup_kernel.resource_dir.startswith(prefix):
            print(
                "Removing existing Jupyter kernel found "
                f"at {old_jup_kernel.resource_dir}"
            )
        ksm.remove_kernel_spec(XONSH_JUPYTER_KERNEL)
    except NoSuchKernel:
        pass

    spec = json.loads((RESOURCES_DIR / "kernel.json").read_text(encoding="utf-8"))
    python = sys.executable
    if sys.platform == "win32" and os.altsep:
        # conda-build / Jupyter on Windows expect forward-slash paths.
        python = python.replace(os.sep, os.altsep)
        if isinstance(prefix, str):
            prefix = prefix.replace(os.sep, os.altsep)
    spec["argv"] = [python if a == "{python}" else a for a in spec["argv"]]

    with tempfile.TemporaryDirectory() as d:
        os.chmod(d, 0o755)  # tempdir starts at 0o700, Jupyter needs world-readable.
        d_path = Path(d)
        with (d_path / "kernel.json").open("w", encoding="utf-8") as f:
            json.dump(spec, f, sort_keys=True, indent=2)

        for resource in RESOURCES_DIR.iterdir():
            if not resource.is_file():
                continue
            name = resource.name
            if name == "kernel.json" or name.startswith("__") or name.endswith(".py"):
                continue
            shutil.copyfile(resource, d_path / name)

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
