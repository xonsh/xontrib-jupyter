<p align="center">
Xonsh provides a kernel for Jupyter Notebook and Lab so you can execute
xonsh commands in a notebook cell without any additional magic.
</p>

<p align="center">  
If you like the idea click ⭐ on the repo and <a href="https://twitter.com/intent/tweet?text=Nice%20xontrib%20for%20the%20xonsh%20shell!&url=https://github.com/xonsh/xontrib-jupyter-shell" target="_blank">tweet</a>.
</p>


## Installation

To install use pip:

```bash
xpip install xontrib-jupyter-shell
# or: xpip install -U git+https://github.com/xonsh/xontrib-jupyter-shell
```

## Usage

```bash
$ xontrib load jupyter
$ xonfig jupyter-kernel
Installing Jupyter kernel spec:
  root: None
  prefix: <env_prefix>
  as user: False
```

`<env_prefix>` is the path prefix of the Jupyter and Xonsh
environment. `xonfig jupyter-kernel --help` shows options for installing
the kernel spec in the user config folder or in a non-standard
environment prefix.

You can confirm the status of the installation:

``` xonshcon
$ xonfig info
+------------------+-----------------------------------------------------+
| xonsh            | 0.9.21                                              |
| Git SHA          | d42b4140                                            |

               . . . . .

| on jupyter       | True                                                |
| jupyter kernel   | <env_prefix>\share\jupyter\kernels\xonsh            |
+------------------+-----------------------------------------------------+
```

Or:

``` xonshcon
$ jupyter kernelspec list
Available kernels:
  python3    <env_prefix>\share\jupyter\kernels\python3
  xonsh      <env_prefix>\share\jupyter\kernels\xonsh
```

## Releasing your package

- Bump the version of your package.
- Create a GitHub release (The release notes are automatically generated as a draft release after each push).
- And publish with `poetry publish --build` or `twine`

## Credits

This package was created with [xontrib cookiecutter template](https://github.com/xonsh/xontrib-cookiecutter).
