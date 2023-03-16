<p align="center">
Xonsh provides a kernel for Jupyter Notebook and Lab so you can execute
xonsh commands in a notebook cell without any additional magic.
</p>

<p align="center">
If you like the idea click ⭐ on the repo and <a href="https://twitter.com/intent/tweet?text=Nice%20xontrib%20for%20the%20xonsh%20shell!&url=https://github.com/xonsh/xontrib-jupyter-shell" target="_blank">tweet</a>.
</p>


## Installation

To install use [xpip](https://xon.sh/aliases.html#xpip):

```xsh
xpip install xontrib-jupyter-shell
# or: xpip install -U git+https://github.com/xonsh/xontrib-jupyter

xontrib load jupyter
xonfig jupyter-kernel --help  # Options for installing.
xonfig jupyter-kernel --user  # Install kernel spec in user config directory.
```

Check the installation:
```xsh
jupyter kernelspec list
# Available kernels:
#  python3    /opt/homebrew/lib/python3.11/site-packages/ipykernel/resources
#  xonsh      /PATH_TO_ENV_PREFIX/share/jupyter/kernels/xonsh

xontrib load jupyter
xonfig jupyter-kernel
# Installing Jupyter kernel spec:
#  root: None
#  prefix: /PATH_TO_ENV_PREFIX/
#  as user: False

xonfig info
#| jupyter          | True
#| jupyter kernel   | /PATH_TO_ENV_PREFIX/share/jupyter/kernels/xonsh

```

## Usage

### Jupyter

Just run [Jupyter Notebook or JupyterLab](https://jupyter.org/) and choose xonsh:

```xsh
jupyter notebook
jupyter lab
```

### Euporie

[Euporie](https://github.com/joouha/euporie) is a terminal based interactive computing environment.

```xsh
euporie-notebook
# Change the kernel to xonsh
```

## Releasing your package 

1. Bump the version of the package.
2. The release notes are automatically generated as a draft release after each PR.
3. Create a GitHub release. 
4. Publish with `poetry publish --build` or `twine`.

## Credits

This package was created with [xontrib cookiecutter template](https://github.com/xonsh/xontrib-cookiecutter).
