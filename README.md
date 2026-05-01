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

[Euporie](https://github.com/joouha/euporie) is a terminal based interactive
computing environment.

```xsh
euporie-notebook --kernel-name xonsh  # or change the kernel in UI
# or
euporie-console --kernel-name xonsh  # or change the kernel in UI
```

## Usage

Subprocess output (e.g. `whoami`, `ls`, `git status`) is captured automatically
and streamed to the notebook cell. Multiline xonsh blocks (`with`, `for`, …)
are detected via `is_complete_request`. The Interrupt button on the kernel
toolbar sends `SIGINT` and aborts the current command.

If you ever need to force xonsh-side capturing (e.g. for tools that write
to a TTY directly), the historical workaround is still available:

```xsh
$XONSH_CAPTURE_ALWAYS = True
$XONSH_SUBPROC_CAPTURED_PRINT_STDERR = True
```

## Testing

Install the project and its development dependencies in editable mode:

```bash
pip install -e '.[dev]'
```

Then start `xonsh` without an rc file, load the xontrib and install the
kernelspec into the current user's profile:

```sh
xonsh --no-rc -c "xontrib load jupyter; xonfig jupyter-kernel --user"
```

Now run a notebook and pick the xonsh kernel:

```sh
jupyter notebook
```

Run the unit tests with `pytest`:

```sh
pytest -v
```

## Known issues

### Pager-based tools

Some tools like the [AWS CLI](https://aws.amazon.com/cli/) shell out to a
non-capturable `less` pager by default. Disable pagination at the tool
level (e.g. `$AWS_PAGER = 'cat'` for AWS CLI).

## Credits

* This package was created with [xontrib cookiecutter template](https://github.com/xonsh/xontrib-cookiecutter).
* [awesome-jupyter](https://github.com/markusschanta/awesome-jupyter) - A curated list of awesome Jupyter projects, libraries and resources.
