# Makefile

## Table of Contents

1. [Introduction](#introduction)
2. [About GNU Make](#about-gnu-make)
3. [Targets](#targets)
4. [Why some targets use stamp files](#why-some-targets-use-stamp-files)
5. [Keeping Help Accurate](#keeping-make-help-accurate)
6. [Adding a new target](#adding-a-new-target)

## Introduction

The top-level `Makefile` is the single entry point for the common development
commands (`uv run pytest`, `uv run ruff check`, `uv run mkdocs build`, ...),
and it's written so that Make's normal file-based dependency tracking
applies: a target's action only runs when its target is missing or older
than its prerequisites.

## About GNU Make 

Think of **GNU Make** as a digital kitchen assistant that follows a recipe to build software.

Instead of forcing a programmer to manually type out dozens of complicated instructions every single time they want to create an app, Make automates the entire process using an instruction manual called a **Makefile**.

**How It Works**

* **Recipes & Dependencies:** The Makefile tells Make what files need to be created (the "targets"), what raw code files are required to make them (the "dependencies"), and the exact steps to build them (the "commands").
* **Smart Updates:** Make checks the timestamp on every file. If you edit a small piece of code, Make only rebuilds the parts affected by that specific change—saving massive amounts of time compared to rebuilding everything from scratch.
* **Universal Usage:** While mainly used for programming languages like C or C++, Make isn't picky. You can use it to automate almost any multi-step computer task, like publishing documentation or installing software.

**Key Advantages**

* **Ease of Use:** Users don't need to know the complex details of how a program is built; they just type `make`, and the tool handles the rest.
* **Handy Shortcuts:** GNU Make includes trick options (like pretending a modified file *wasn't* changed) to prevent unnecessary, time-consuming recompilations.
* **Free & Open:** Unlike proprietary tools, GNU Make is completely free open-source software, making it a standard tool across the software industry.


## Targets

| Target | What it does | Rebuilds when... |
|---|---|---|
| `make flight_data` | Loads OpenFlights/OurAirports data into `data/processed/flight_data.db` | `src/data/flight_data.py` is newer than the DB file |
| `make test` | Runs `uv run pytest` | Any file under `src/`, `tests/`, or `pyproject.toml` changed since the last **passing** run |
| `make lint` | Runs `uv run ruff check` | Any file under `src/` or `pyproject.toml` changed since the last passing run |
| `make check` | `lint` + `test` | (aggregate of the above) |
| `make docs` | Runs `uv run mkdocs build` → `site/` | Any file under `docs/`, `src/`, or `mkdocs.yml` changed since the last build |
| `make docs-serve` | Runs `uv run mkdocs serve` (live preview) | Always — it's a long-running server, not a build artifact |
| `make notebook` | Runs `uv run jupyter lab` | Always |
| `make all` | `check` + `docs` | (aggregate) |
| `make clean` | Removes `data/processed/flight_data.db`, `site/`, and `.make/` | — |
| `make help` | Lists all targets with their one-line descriptions | Always |

Run `make` with no target and it runs `help` (`.DEFAULT_GOAL := help`), so
`make` on its own is a safe way to see what's available.

## Keeping `make help` accurate

Each target has a `## description` comment after its prerequisites, e.g.:

```make
test: $(STAMP_DIR)/test ## Run the pytest suite
```

`help` greps the Makefile for lines matching `target: ... ## text` and prints
the name/description pairs. When adding a new target, add a `## ...` comment
in the same style so it shows up automatically — nothing else to wire up.

## Why some targets use stamp files

Make decides whether to run a target's recipe by comparing the modification
time of the target file to its prerequisites. That works cleanly for
`flight_data` and `docs`, which produce a real output file
(`flight_data.db`, `site/index.html`).

`test` and `lint` don't produce a file — `pytest`/`ruff check` just print
results and exit. To still get "only run if something changed" behavior,
each writes an empty stamp file under `.make/` on success:

```make
$(STAMP_DIR)/test: $(PY_SRC) $(PY_TESTS) pyproject.toml | $(STAMP_DIR)
	uv run pytest
	touch $@

test: $(STAMP_DIR)/test
```

`test` is a `.PHONY` alias for the real target `.make/test`. Make compares
`.make/test`'s timestamp against every file in `$(PY_SRC)` and `$(PY_TESTS)`;
if none are newer, it reports "Nothing to be done" and skips running pytest.

Because the `touch $@` only runs if the command above it (`uv run pytest`)
exits successfully, a **failing** run never updates the stamp — so a broken
test suite reruns on every `make test` until it's fixed, instead of being
cached as "done." `.make/` is gitignored; delete it (or run `make clean`) to
force everything to rerun regardless of timestamps.

## Adding a new target

- If the command produces a real output file, key the target on that file's
  path and list its real inputs as prerequisites (see `flight_data` or
  `docs`).
- If it doesn't (a check, a report, anything that just exits 0/1), use the
  stamp-file pattern above under `$(STAMP_DIR)`.
- If it's inherently non-idempotent or long-running (a server, a REPL), just
  mark it `.PHONY` with no target file, like `docs-serve` and `notebook`.
