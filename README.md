<p align="center">
Xonsh kernel for Jupyter Notebook and Jupyter Lab allows to execute
xonsh shell commands in a notebook cell.
</p>

<p>
<img src="https://repository-images.githubusercontent.com/471969357/c372c71d-2baa-4804-9e01-d7305316b500">
</p>

<p align="center">
If you like the idea click ⭐ on the repo and <a href="https://twitter.com/intent/tweet?text=Nice%20xontrib%20for%20the%20xonsh%20shell!&url=https://github.com/xonsh/xontrib-jupyter" target="_blank">tweet</a>.
</p>


## Installation

To install use [xpip](https://xon.sh/aliases.html#xpip):

```xsh
xpip install xontrib-jupyter
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

### Jupyter

Just run [Jupyter Notebook or JupyterLab](https://jupyter.org/) and choose xonsh:

```xsh
jupyter notebook
# or
jupyter lab
```

### Euporie

[Euporie](https://github.com/joouha/euporie) is a terminal based interactive computing environment.

```xsh
euporie-notebook --kernel-name xonsh  # or change the kernel in UI
# or
euporie-console --kernel-name xonsh  # or change the kernel in UI
```

## Usage

By default Jupyter is not capturing the output and you can have empty result when you're running a command e.g.  `whoami`. Read about and use [`$XONSH_CAPTURE_ALWAYS`](https://xon.sh/envvars.html#xonsh-capture-always) to manage capturing on xonsh side. 

```xsh
whoami
# <empty>

$XONSH_CAPTURE_ALWAYS = True
whoami
# snail
```

## Testing

- install the project with its dependencies
```bash
poetry install
poetry install --only-root
```
- now start the xonsh shell

```sh
xonsh --no-rc
```

- inside the xonsh shell, you can load the jupyter xontrib and install the kernel

```sh
xontrib load jupyter

# this will install the kernel
xonfig jupyter-kernel --user

# now start a notebook and choose xonsh kernel
jupyter notebook
```

## Releasing your package

1. Create a [GitHub release](https://github.com/xonsh/xontrib-jupyter/releases/new) with the desired version number as the tag (e.g. v0.3.3).
2. It will automatically build the package and upload it to the PyPI.

## Known issues

### Uncaptured output

In some cases you need to enable capturing first:

```xsh
$XONSH_CAPTURE_ALWAYS = True
$XONSH_SUBPROC_CAPTURED_PRINT_STDERR = True
```

### Uncaptured output because of pager

Some tools like [AWS CLI](https://aws.amazon.com/cli/) using the uncapturable `less` pager to show the output by default. In these cases you need to find the way to disable the pager e.g. set [`$AWS_PAGER = 'cat'`](https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-pagination.html#cli-usage-pagination-awspager) for AWS CLI.

## Credits

* This package was created with [xontrib cookiecutter template](https://github.com/xonsh/xontrib-cookiecutter).
* [awesome-jupyter](https://github.com/markusschanta/awesome-jupyter) - A curated list of awesome Jupyter projects, libraries and resources.
