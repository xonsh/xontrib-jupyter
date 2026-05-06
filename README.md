<p align="center">
Xonsh kernel for Jupyter Notebook and Jupyter Lab allows to execute
xonsh shell commands in a notebook cell.
</p>

<p>
<img width="1000" height="563" alt="image" src="https://github.com/user-attachments/assets/d7c96b9c-deb1-46af-9980-d3b6b71dcffb" />

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

## Interactive widgets

`ipywidgets`, `IPython.display`, pandas/matplotlib rich repr, and the
`comm` channel all work — the kernel inherits `ipykernel.IPythonKernel`,
so widget views, slider observers, and button callbacks behave as in a
plain Python kernel. The difference: callbacks can use the full xonsh
syntax, including subprocess pipelines and `@(...)` substitutions.

Below — a slider that picks a size threshold (MB) plus a button that
lists every file at or above that size under `/usr`, sorted largest
first. The output area is cleared on every click so each run gives a
fresh result.

```python
from ipywidgets import IntSlider, Button, Output, VBox
from IPython.display import display

slider = IntSlider(value=10, min=1, max=200, step=1, description="MB ≥")
button = Button(description="Find files", button_style="success")
out = Output()

@button.on_click
def _(_):
    out.clear_output()
    with out:
        mb = slider.value
        print(f"Files ≥ {mb} MB under /usr:")
        find /usr -type f -size +@(mb)M -print0 2>/dev/null | xargs -0 du -h 2>/dev/null | sort -hr | head -30

display(VBox([slider, button, out]))
```

Drag the slider, hit *Find files*, and the cell repopulates from a fresh
`find … | xargs du | sort` pipeline that ran inside the click handler.
`@(mb)` interpolates the current slider value into the subprocess
arguments — that's pure xonsh syntax executing inside an `ipywidgets`
callback.

The next example samples total CPU usage 10 times via `ps -A -o %cpu` and
renders the series as an inline matplotlib chart. The first import block
configures the inline backend once per kernel session — `%matplotlib
inline` is unavailable because xonsh's parser does not understand IPython
magics, so the equivalent is invoked directly through the
`matplotlib_inline` package:

```python
import time
import matplotlib.pyplot as plt
import matplotlib_inline.backend_inline as _mib
_mib.configure_inline_support(get_ipython(), "inline")

samples = []
for i in range(10):
    cpu = float($(ps -A -o %cpu | awk '{s+=$1} END {print s}'))
    samples.append(cpu)
    print(f"sample {i + 1}: {cpu:.1f}%")
    time.sleep(0.3)

def show_chart():
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(samples, marker="o", linewidth=2)
    ax.set(xlabel="sample #", ylabel="total CPU %",
           title="CPU usage over 10 samples")
    ax.grid(True, alpha=0.3)
    plt.show()

show_chart()
```

`$(ps -A -o %cpu | awk '...')` runs a real shell pipeline and returns the
captured stdout as a string — the conversion to `float` happens in
Python. Wrapping the matplotlib calls in `show_chart()` keeps every
intermediate `Axes`/`Line2D` object out of the cell output so only the
final rendered figure is published as an `image/png` MIME bundle.

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
