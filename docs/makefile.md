# Makefile

## Table of Contents

1. [Introduction](#introduction)
2. [About GNU Make](#about-gnu-make)
3. [Targets](#targets)
4. [Why some targets use stamp files](#why-some-targets-use-stamp-files)
5. [How the final report is assembled](#how-the-final-report-is-assembled)
6. [Keeping Help Accurate](#keeping-make-help-accurate)
7. [Adding a new target](#adding-a-new-target)
8. [Known issues](#known-issues)

## Introduction

The top-level `Makefile` is the single entry point for the common development
commands (`uv run pytest`, `uv run ruff check`, `pandoc`, ...),
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

### Building the data

| Target | What it does | Rebuilds when... |
|---|---|---|
| `make flight_data` | Loads the raw OpenFlights/OurAirports files into `data/processed/flight_data.db` | `src/data/flight_data.py` is newer than the DB file |
| `make international_airports` | Scrapes Wikipedia's list of international airports to `data/processed/international_airports.csv` | The scraper or the raw JSON changed |
| `make flight_network` | Builds `data/processed/{airports,routes}.csv` **and** the `airports`/`routes` DB tables, with pandas | The builder or any raw input changed |
| `make verify_iata_codes` | Re-checks `data/reference/iata_code_overrides.csv` against iata.org | Always (makes network requests) |
| `make united_airlines_tables` | Derives the United subset tables inside the DB for ad-hoc SQL | The SQL file or the DB changed |

`flight_network` is the one that matters day to day. It needs only pandas — a
clone without the `sqlite3` binary can still build the dataset and run every
test. `united_airlines_tables` is the sole target that still requires that
binary, and it is optional exploration rather than part of the build.

### Freezing data and creating experiments

| Target | What it does |
|---|---|
| `make snapshot` | Freezes `data/processed` as an immutable, checksummed snapshot under `data/snapshots/` |
| `make snapshot SNAPSHOT_FILTERS="..."` | Freezes a narrowed slice; filters are the catalog's own |
| `make legacy_snapshot` | Shorthand for the United / large / US slice |
| `make experiment SLUG=<name>` | Scaffolds an experiment directory with runnable starter code |
| `make experiment SLUG=<name> CODE=run.py` | The same, as a script rather than a notebook |

```bash
make snapshot SNAPSHOT_FILTERS="--airline UA --airport-type large --country US"
make experiment SLUG=astar-heuristics SNAPSHOT=2026-09-11-bb90a8
make experiment SLUG=astar-heuristics CODE=run.py
```

`CODE=` names the file holding the experiment's code, and its extension picks
the starter: a name ending in `.py` gets a script that locates itself with
`__file__`, anything else gets a notebook that uses `Path.cwd()`. Both open the
experiment, verify the snapshot, ask it something and record the answer.
`FORCE=1` regenerates `experiment.toml` for an experiment that already exists;
it never touches code files.

Identical data always lands on the same snapshot id, so re-freezing a slice is
a no-op rather than a duplicate. See [Experiments](experiments.md) for what
these produce and how to use it.

### Quality gates and everything else

| Target | What it does | Rebuilds when... |
|---|---|---|
| `make test` | Runs `uv run pytest` | Any file under `src/`, `tests/`, `scripts/`, or `pyproject.toml` changed since the last **passing** run |
| `make lint` | Runs `uv run ruff check` | Any file under `src/` or `pyproject.toml` changed since the last passing run |
| `make check` | `lint` + `test` | (aggregate of the above) |
| `make docs` | Renders every `docs/*.md` to PDF, plus the assembled report with `pandoc` → `build/pdf/` | The matching `.md`, the LaTeX header, the SVG filter, or any generated diagram is newer than the PDF |
| `make report` | Concatenates `docs/report/*.md` into a single `build/pdf/report.pdf`, with a table of contents | Any chapter, the frontmatter, `newpage.md`, the LaTeX header, the SVG filter, or any generated diagram is newer than the PDF |
| `make diagrams` | Renders `mermaid/*.mmd` to a committed `docs/images/*.svg` and a generated `build/png/*.png` | The `.mmd` is newer than its output |
| `make notebook` | Syncs the `notebooks` dependency group, then runs `uv run jupyter lab` | Always |
| `make all` | `check` | (aggregate) |
| `make clean` | Removes the generated CSVs, `data/processed/flight_data.db`, `build/`, and `.make/` | — |
| `make help` | Lists all targets with their one-line descriptions | Always |

`make clean` does **not** remove `data/snapshots/` or `experiments/`. Those are
committed artifacts, not build output — that distinction is the whole point of
a snapshot.

Run `make` with no target and it runs `help` (`.DEFAULT_GOAL := help`), so
`make` on its own is a safe way to see what's available.

## How the final report is assembled

`make report` is the one target that builds a single PDF from many markdown
files. The chapters live in [`docs/report/`](report/README.md), one file each,
and `REPORT_CHAPTERS` in the Makefile lists them in the document's order —
listed rather than globbed, because `ls` order stops matching reading order the
moment a chapter is renamed or inserted.

Between every pair of chapters the recipe passes `docs/report/newpage.md`, a
file whose entire contents is a bare `\newpage`. Pandoc concatenates its inputs
before parsing, so the directive lands between the chapters and starts each one
on a fresh page. Keeping it in its own file is what keeps it out of GitHub:
GitHub renders each chapter on its own, and a `\newpage` written inline would
show up there as literal text.

To add a chapter, write the file and add it to `REPORT_CHAPTERS`. Nothing else
needs to change — `$(REPORT_SRCS)` interleaves the page breaks, the PDF's
prerequisites are derived from the same list, and the new chapter appears in the
contents automatically.

### The table of contents

`REPORT_TOC_FLAGS` adds `--toc --toc-depth=3`, and only the `report` target
passes it: the other docs are single-topic and short enough that a contents page
would be noise. Depth counts from `#`, so 3 reaches the `###` subsections —
which matters, because §6 and §7 carry six subsections each and are the sections
a reader is most likely to jump straight to.

Two details are worth knowing if the contents page ever looks wrong:

- **It needs its own page**, and LaTeX will not break there by itself. The
  chapters' `newpage.md` breaks sit *between* chapters, so without help the
  introduction would start halfway down the contents page.
  `doc-header.tex` appends a `\newpage` to `\tableofcontents` to close it. That
  hook is inert for every other document, which never calls the macro.
- **The report's `#` heading is deliberately absent from it.** It repeats the
  title page, so an entry for it would point at the whole document.
  `00-frontmatter.md` marks it `{.unnumbered .unlisted}` — `.unlisted` is what
  keeps it out, and pandoc requires `.unnumbered` alongside. Neither changes how
  it looks, since pandoc leaves every heading unnumbered already.

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
(`flight_data.db`, `build/pdf/*.pdf`).

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
  mark it `.PHONY` with no target file, like `notebook`.

## Known issues

### TODO: `make docs` drops hand-authored `.svg` diagrams

**Status:** open, narrowed. **Affects:** `distance_formulas.md`.

`docs/svg-to-png.lua` rewrites the source of every `.svg` image to
`build/png/<name>.png`:

```lua
function Image(el)
  local name = el.src:match("([^/]+)%.svg$")
  if name then
    el.src = root .. "/build/png/" .. name .. ".png"
  end
  return el
end
```

Only diagrams with a mermaid source get a matching PNG. `$(PNGS)` is built
from `mermaid/*.mmd`, so a `.svg` that was drawn by hand has nothing to
generate its PNG, and the rewritten path points at a file that does not exist.

Pandoc treats a missing image as a warning rather than an error, so the build
still exits 0 and the PDF is simply missing its figures. To confirm:

```bash
make build/pdf/distance_formulas.pdf
pdfimages -list build/pdf/distance_formulas.pdf
# header row only -- zero images, despite the four figures the markdown references
```

The four affected files — `great_circle.svg`, `ellipsoid_geodesic.svg`,
`equirectangular.svg` and `utm_projection.svg` — have no `.mmd` source.

Two ways out:

1. **Give the filter a fallback.** When `build/png/<name>.png` does not exist,
   resolve to the committed `docs/images/<name>.png` instead. All four already
   have one committed beside the `.svg`.
2. **Add a rule that converts a committed `.svg` to `build/png/`.** Note that
   `rsvg-convert` is the obvious tool and is already checked by `make
   check-deps`, but it drops all text from a *mermaid* SVG; it is fine for
   these hand-drawn ones.

Whichever is chosen, a missing figure should fail the build rather than pass
quietly.

### Fixed: mermaid diagrams were never generated

Previously `$(DOCS_MERMAID)` pointed at `docs/mermaid/`, which holds only a
`.gitkeep`, while the actual sources live in `mermaid/` at the repository
root. `$(PNGS)` expanded to nothing and `build/png/` was never created, so
every diagram was dropped from every PDF.

`MERMAID_DIR` now points at `mermaid/`, and `.mmd` renders straight to `.png`
via `mmdc`. The intermediate `.svg` step was removed because `rsvg-convert`
silently drops all text from a mermaid SVG. See [`make diagrams`](#targets).
