# Traiectoria-optima

Class project for San Jose University graduate course CMPE-180A

## About the name

_Traiectoria-optima_ is a Latin phrase that translates directly to "optimal trajectory" or "best path."

It combines two classical Latin roots:

- **Traiectoria** (from traiicere): A crossing, passage, or path described by a moving object.

- **Optima** (feminine form of optimus): Best, most favorable, or ideal.






## Development Environment Setup with `uv`

This project uses [uv](https://docs.astral.sh/uv/) to manage the Python
interpreter, the virtual environment, and the locked dependency set
(`pyproject.toml` + `uv.lock`). Python 3.12 or newer is required; `uv` will
download a suitable interpreter for you, so a pre-installed Python is not
needed.

### 1. Install `uv`

**macOS**

```bash
# Recommended: standalone installer
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv
```

Restart your shell (or `source ~/.zshrc`) so `uv` is on your `PATH`.

**Windows**

```powershell
# Recommended: standalone installer (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with winget
winget install --id=astral-sh.uv -e
```

Open a new PowerShell window afterwards so the updated `PATH` takes effect.

Verify the install on either platform:

```bash
uv --version
```

### 2. Clone the repository

```bash
git clone https://github.com/<your-org>/traiectoria-optima.git
cd traiectoria-optima
```

### 3. Create the environment and install dependencies

```bash
uv sync
```

This creates a `.venv` in the project root, installs the pinned Python
version, and installs every dependency exactly as recorded in `uv.lock`.
Re-run `uv sync` any time you pull changes that touch `pyproject.toml` or
`uv.lock`.

### 4. Run things in the environment

The idiomatic approach is to prefix commands with `uv run` — no manual
activation required, and `uv` keeps the environment in sync automatically:

```bash
uv run python src/models/flight_model.py
uv run jupyter lab
```

If you prefer an activated shell:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (cmd.exe)
.venv\Scripts\activate.bat
```

Deactivate with `deactivate`.

### 5. Jupyter notebooks

Launch JupyterLab through `uv` so the kernel resolves to the project
environment:

```bash
uv run jupyter lab
```

Notebooks live in `notebooks/`. If a notebook does not see the project
packages, select the kernel that points at `.venv` (registered by the
`ipykernel` dependency), or register it explicitly:

```bash
uv run python -m ipykernel install --user --name traiectoria-optima
```

### 6. Managing dependencies

```bash
uv add <package>            # add a runtime dependency
uv add --dev <package>      # add a development-only dependency
uv remove <package>         # drop a dependency
uv lock --upgrade           # refresh the lock file to newest allowed versions
```

`uv add`/`uv remove` update both `pyproject.toml` and `uv.lock`; commit both
files together.

### Troubleshooting

- **`uv: command not found` / not recognized** — reopen the terminal so the
  installer's `PATH` change applies.
- **PowerShell blocks the install script** — run it in the form shown above,
  which sets `-ExecutionPolicy ByPass` for that single invocation only.
- **Environment feels stale or broken** — delete `.venv` and run `uv sync`
  again; the lock file makes this cheap and reproducible.

## Data Sets

- [Open Flights](https://openflights.org/data.php)

- [Our Airports](https://ourairports.com/data/)
