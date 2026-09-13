# Tutorial: your first experiment

You will build an experiment: a directory holding a question, the data it was
asked of, and the answer, committed together. Look at the flight network, freeze
a slice of it as a **snapshot**, ask that snapshot a question, record what came
back. About half an hour.

Nothing to read first. [Experiments](experiments.md) is the reference, and each
step links into it. The output blocks come from a real run, so you can compare
yours. Works locally or in **Google Colab**, with an **In Colab** box wherever
the two differ.

Your question:

> What does it cost to skip a stop?

Fewest kilometres and fewest legs are two different routes. You will measure the
gap on three pairs of US airports, and find that one of the three is lying about
it. A finished copy sits at `experiments/shortest-vs-fewest/` to check yourself
against at the end; yours gets a name of its own.

## Before you start

**What you need.** Step 1 installs the first two; the rest is either already on
your machine or optional.

| | Why | Where |
|---|---|---|
| A terminal and `git` | Cloning, branching, and two commits at the end | — |
| `uv` | Installs Python 3.12 and every dependency. You do not need Python already — `uv` brings its own | [Setup §1](setup.md#1-install-uv) |
| `make` | Steps 3 and 4 only, and only as a convenience. Its recipes are POSIX shell and call `uv run`, so it needs both | [Makefile](makefile.md) |
| JupyterLab | **Step 5a only.** Skip it if you take the script route | [Setup §5](setup.md#5-jupyter-notebooks) |
| A browser and a Google account | The alternative to all of the above — nothing installed, and the recommended route on Windows | [Setup §6](setup.md#6-google-colab) |

No `make`? Nothing is lost. It only wraps two scripts, and the **In Colab**
boxes in Steps 3 and 4 give the direct commands, which work anywhere Python
does.

**On Windows, use Colab.** `uv` and `git` both install natively, but the
Makefile's recipes are POSIX shell — `mkdir -p`, `touch`, `test -n` — so they
need a Unix shell, which installing `make` on its own does not give you. Colab
needs neither, and the whole tutorial runs there unadapted. If you want a local
checkout, `wsl --install` provides the shell, and every instruction below then
reads as written.

**What you should already know.** Enough Python to read a loop and edit a
function — no knowledge of this project's library is assumed, and every symbol
it uses is introduced where it appears. Beyond that: `git add`, `git commit`
and `git checkout -b`; and that a `.toml` file is `key = value` lines under
`[section]` headings. Shortest-path algorithms are the subject, not a
prerequisite.

**What to read.** Nothing, first. This tutorial is the entry point, and it links
out where detail helps. Afterwards, or alongside if you want the reasoning
behind a step:

| | |
|---|---|
| [Experiments](experiments.md) | The same machinery as a reference: every snapshot filter, the narrowing vocabulary, the endpoint modes. The natural next read |
| [Setup](setup.md) | If Step 1 gives you trouble, or you want the Colab install explained line by line |
| [Report §4 *Algorithms*](report/04-algorithms.md) | If Dijkstra and BFS are new. Step 6 turns on the difference between them, and works without prior reading — but this is where the theory lives, alongside Goodrich, Tamassia & Goldwasser ch. 14 |
| [Makefile](makefile.md) | Every target, including the two this tutorial uses |
| [Demos](demos.md) | Small runnable scripts, one idea each, once you want to poke at the library directly |

---

## Step 1 — Get the repository and its dependencies

Starting from nothing, three commands. [Setup](setup.md) covers each in full —
this is the short path through it.

**Install `uv`**, which manages the Python version, the virtual environment and
the dependencies ([Setup §1](setup.md#1-install-uv) has Linux and Windows, and
the Homebrew alternative):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Clone the repository** ([Setup §2](setup.md#2-clone-the-repository)):

```bash
git clone https://github.com/dgwartney/traiectoria-optima.git
cd traiectoria-optima
```

**Build the environment** ([Setup
§3](setup.md#3-create-the-environment-and-install-dependencies)):

```bash
uv sync
```

That creates `.venv/` in the project root and installs the project and its
dependencies at the versions pinned in `uv.lock`. It takes a minute the first
time. You never activate it by hand — prefixing a command with `uv run` runs it
inside that environment ([Setup
§4](setup.md#4-run-things-in-the-environment)), which is why every command below
starts that way.

Check that it worked:

```console
$ uv run python -c "from flight_planner.experiments import Snapshot; print('ok')"
ok
```

If that prints `ok`, you have everything this tutorial needs. Run the rest of
the commands from the repository root unless a step says otherwise.

**Now make yourself a branch.** This tutorial writes files into the repository —
a snapshot, an experiment directory, a couple of commits — and you want them
somewhere you can throw away:

```bash
git checkout -b tutorial/<your-name>
```

Use something that identifies you: `tutorial/dgwartney`, `tutorial/ana`. When
you are done you can merge it, keep it, or delete it with
`git checkout main && git branch -D tutorial/<your-name>` — nothing on `main`
will have moved.

### In Colab instead

Every step below works in Colab, and the answers come out the same. What differs
is the plumbing: the `make` targets are out, because the ones this tutorial uses
run `uv run python` (`Makefile`) and the setup cell below installs with `pip3`
rather than `uv`, and your working directory is not the experiment's. Wherever
that matters there is an **In Colab** box like this one, giving the command that
does work.

Start with one cell in place of the three commands above ([Setup
§6](setup.md#6-google-colab) explains each line, and why `pip install -e` is the
wrong choice here):

```python
!rm -rf /content/traiectoria-optima
!git clone --depth 1 https://github.com/dgwartney/traiectoria-optima.git /content/traiectoria-optima
!pip3 install -q /content/traiectoria-optima
```

Then the same check:

```python
from flight_planner.experiments import Snapshot
print('ok')
```

Two consequences to carry through the rest of the tutorial:

- **`uv run python …` becomes `!python …`**, run from the clone. The scripts
  behind the `make` targets import only pandas, the installed package and the
  standard library, so a plain interpreter runs them.
- **Your working directory is not the experiment directory.** Colab starts you
  in `/content`, not in `experiments/<slug>/`, so anywhere this tutorial says
  `Path.cwd()` you pass the experiment's path instead.

Branching still applies — `!git -C /content/traiectoria-optima checkout -b
tutorial/<your-name>` — though a Colab clone is disposable anyway. Step 7 covers
getting the work back out.

---

## Step 2 — Look at the data before freezing any of it

> **In Colab** — there is no REPL to start; each `>>>` block below is a cell,
> without the prompts. The one edit is the path: nothing resolves against a
> repository root, so open the snapshot from the clone —
> `Snapshot.open('/content/traiectoria-optima/data/snapshots/2026-09-11-bb90a8')`.
> The counts are the same.

Start a Python session:

```console
$ uv run python
Python 3.12.12 (main, Jan 14 2026, 23:36:32) [Clang 21.1.4 ] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

The repository ships a frozen copy of the whole network, so there is something
to look at immediately:

```pycon
>>> from flight_planner.experiments import Snapshot
>>> catalog = Snapshot.open('data/snapshots/2026-09-11-bb90a8').catalog()
>>> catalog
Catalog(3387 airports, 66332 routes, unnarrowed)
```

Opening a snapshot re-hashes every file against its manifest first — it is
fast enough that you will not notice, and it means the numbers below came from
data that is provably unchanged. 66,332 routes between 3,387 airports,
worldwide: more than this experiment needs, and a smaller scope is easier to
reason about.

```pycon
>>> us = catalog.airport_type('large').country('US')
>>> us
Catalog(94 airports, 7005 routes, airport_type -> country)
>>> len(us.routes), len(us.airports)
(7005, 94)
```

94 airports, 7,005 routes between them — and the catalog remembers how it was
derived (`airport_type -> country`), which is what will end up in the snapshot's
manifest. Narrowing returns a *new* catalog and leaves the original alone, so
you can try a scope, look at the size, and try a different one. Nothing is
written to disk until you say so:

```pycon
>>> catalog
Catalog(3387 airports, 66332 routes, unnarrowed)
```

Check that the airports we want to ask about survived the narrowing:

```pycon
>>> for code in ('SFO', 'BOS', 'BOI', 'CHS', 'HNL', 'BDL'):
...     print(code, us.airport(code).name)
...
SFO San Francisco International Airport
BOS Boston Logan International Airport
BOI Boise Air Terminal/Gowen Field
CHS Charleston International Airport
HNL Daniel K. Inouye International Airport
BDL Bradley International Airport
```

Individual airports carry their own description, so you never have to guess what
a code means:

```pycon
>>> us.airport('SFO')
Airport('SFO', city='San Francisco', lat=37.619806, lon=-122.374821)
```

**That was the design step.** `airport_type('large')` and `country('US')` are
the scope this experiment should run against — and they are the same words we
are about to hand to the command that freezes it.

Leave the session with `exit()` or Ctrl-D.

---

## Step 3 — Freeze it

A snapshot is a copy of the data that cannot change without the change being
caught. First make sure the processed files are current:

```console
$ make flight_network
uv run python src/data/flight_network.py \
        data/raw/our_airports/airports.csv \
        data/raw/open_flights/routes.dat \
        data/processed/airports.csv \
        data/processed/routes.csv \
        --international data/processed/international_airports.csv \
        --database data/processed/flight_data.db
airports: 3387  routes: 66332
routes dropped for unresolvable endpoints: 1331
touch .make/flight_network
```

On a fresh clone this always runs: it rebuilds `data/processed/` from the raw
downloads, and the stamp file that records "already built" is not committed.
**3,387 airports and 66,332 routes** — the same totals you saw in Step 2, which
is the first sign that your data matches this tutorial's. The 1,331 dropped
routes reference airports that no longer exist or have been renamed; the
pipeline reports them rather than discarding them silently
([Experiments §9](experiments.md#9-things-to-know-before-you-rely-on-this)).

Run it a second time and nothing happens, because nothing changed:

```console
$ make flight_network
make: Nothing to be done for `flight_network'.
```

### Why the rebuild did not change anything

Look at what git thinks happened:

```console
$ git status --short data/processed/
```

Nothing. You just regenerated those files and they came out **byte-for-byte
identical** to the ones you cloned.

That is by design, and it is worth understanding before you freeze anything:

- **`data/processed/airports.csv` and `routes.csv` are committed to the
  repository.** They arrive with the clone; you did not have to build them at
  all. Running `make flight_network` was a check, not a prerequisite.
- **The raw downloads are committed too**, under `data/raw/`. The pipeline reads
  those local files and nothing else — no API call, no download, no "latest"
  anything. Look back at the command it printed: every path is a file in the
  repository.
- **So the same inputs produce the same output, on every machine.** That is why
  your snapshot in a moment gets the same hash suffix as mine.

These files do change — but only when someone improves the pipeline and commits
new output, deliberately, as a reviewable diff. What they never do is drift
underneath you between one run and the next.

Which raises the obvious question: if the processed files are already committed
and stable, why freeze a copy at all? Because "stable" is a property of today.
The pipeline *is* improved, the file names never change when it happens, and a
notebook reading `data/processed/` directly would silently start answering a
different question. A snapshot is how you opt out of that — see
[Experiments §1](experiments.md#1-the-problem-this-solves).

> **In Colab** — skip the rebuild entirely. The target runs `uv run python`,
> and the rebuild was only ever a check: the processed files arrive with the
> clone, as the section above explains. Go straight to freezing.

Now freeze the slice:

```console
$ make snapshot SNAPSHOT_FILTERS="--airport-type large --country US"
processed: 66332 routes / 3387 airports
  airport_type(large_airport) -> 50474 routes / 1062 airports
  country(US) -> 7005 routes / 94 airports
snapshot: data/snapshots/2026-09-12-3e4f9d
  7005 routes / 94 airports
```

> **In Colab** — `make snapshot` is a thin wrapper around a script, so call the
> script. Move into the clone once, and everything after this is a relative
> path like the tutorial's:
>
> ```python
> %cd /content/traiectoria-optima
> !python scripts/new_snapshot.py \
>     --airports-csv data/processed/airports.csv \
>     --routes-csv data/processed/routes.csv \
>     --root data/snapshots \
>     --airport-type large --country US
> ```
>
> That prints the report above, line for line, `3e4f9d` suffix included.

Read that output before scrolling past — it is the only time you are shown it.
The indented lines are your two filters applied one at a time. **They should
end on 7,005 routes and 94 airports, the numbers you saw in Step 2.** If they
do, you froze the scope you meant to.

The last two lines name what was written. `2026-09-12-3e4f9d` is the snapshot's
**id**, and it is also the directory's name.

### Reading the id

An id is `<date>-<content hash>`. The two halves answer different questions, and
only the second one is about your data.

**The hash should be `3e4f9d`.** It is computed from the rows themselves, so the
same slice of the same processed data produces it on any machine, on any day.
That is the line to check. If your suffix differs, your processed data is not
what this tutorial was written against — nothing is broken, but your numbers
will diverge from the ones printed below.

**The date is just today's.** Which means what you see next depends on when you
are reading this:

- **On a later day**, you get a directory of your own — `2026-11-04-3e4f9d`, say
  — sitting beside the committed `2026-09-12-3e4f9d`. Two directories, identical
  rows. That is expected and harmless: equal suffixes mean equal data.
- **On 2026-09-12 itself**, the id you compute *is* the committed one, so the
  freeze lands in the directory that is already there. The CSVs and every
  checksum are rewritten with the same bytes, and only the manifest's `created`
  and `source_commit` change.

From here on, substitute your own id wherever you see `2026-09-12-3e4f9d`.

### See what it wrote

Ask git what just changed. On a later day, the whole directory is new:

```console
$ git status
On branch tutorial/dgwartney
Untracked files:
  (use "git add <file>..." to include in what will be committed)
	data/snapshots/2026-11-04-3e4f9d/

nothing added to commit but untracked files present (use "git add" to track)
```

On 2026-09-12, where you rewrote the committed snapshot with identical rows,
only the manifest moves:

```console
$ git status
On branch tutorial/dgwartney
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   data/snapshots/2026-09-12-3e4f9d/manifest.json

no changes added to commit (use "git add" and/or "git commit -a")
```

Two lines of it, and you can see which:

```console
$ git diff data/snapshots/2026-09-12-3e4f9d/manifest.json
diff --git a/data/snapshots/2026-09-12-3e4f9d/manifest.json b/data/snapshots/2026-09-12-3e4f9d/manifest.json
index 3e3d803..2cab543 100644
--- a/data/snapshots/2026-09-12-3e4f9d/manifest.json
+++ b/data/snapshots/2026-09-12-3e4f9d/manifest.json
@@ -1,7 +1,7 @@
 {
   "snapshot_id": "2026-09-12-3e4f9d",
-  "created": "2026-09-12T02:04:27+00:00",
-  "source_commit": "4087d45828c2c2e1dde8f59befadde844703b0df",
+  "created": "2026-09-12T17:29:09+00:00",
+  "source_commit": "f831c7ddb713812432cef45659f259345ffddef5",
   "generator": "scripts/new_snapshot.py",
   "criteria": {
     "airport_type": "large_airport",
```

When it was made, and from which commit. Your two values will differ from
these, and that is the whole diff: the checksums, the row counts and the
criteria are all unchanged, because the rows are.

Either way nothing is wrong — you asked for the data and got the data. And
either way the directory holds the same three files:

```console
$ ls data/snapshots/2026-09-12-3e4f9d
airports.csv	manifest.json	routes.csv
```

Two CSV files and a manifest recording a SHA-256 checksum for each of them,
plus the narrowing that produced the slice. Commit it:

```bash
git add data/snapshots/2026-09-12-3e4f9d
git commit -m "Freeze the US large-airport network"
```

```console
$ git log -1
commit c14f88dd9e5f28322269d5c54e9d3e98130c2c68 (HEAD -> tutorial/dgwartney)
Author: David Gwartney <david.gwartney@gmail.com>
Date:   Sat Sep 12 10:35:08 2026 -0700

    Freeze the US large-airport network
```

The data is now versioned like anything else in the repository, on your branch,
with a hash of its own. Your commit, author and date will differ from these.

---

## Step 4 — Scaffold the experiment

An experiment is a directory: a config file that pins a snapshot, one or more
notebooks, and the results. The scaffolder writes the first two for you:

**Give your experiment a name of its own.** `shortest-vs-fewest` is already
taken — it is the finished version, committed to this repository — and the
scaffolder refuses to overwrite an experiment that exists:

```console
$ make experiment SLUG=shortest-vs-fewest SNAPSHOT=2026-09-12-3e4f9d
experiments/shortest-vs-fewest/experiment.toml already exists; pass --force to overwrite it
```

So add your identifier, the same one you used for the branch:

```bash
make experiment SLUG=shortest-vs-fewest-dg SNAPSHOT=2026-09-12-3e4f9d \
    DESCRIPTION="What does it cost to skip a stop?"
```

> **Writing a script rather than a notebook?** Step 5 puts that choice in front
> of you properly, but if you already know, add `CODE=run.py` to the command
> above and the scaffolder writes a starter script instead. Everything else in
> this step is the same.

```console
experiment: experiments/shortest-vs-fewest-dg
  snapshot: ../../data/snapshots/2026-09-12-3e4f9d (2026-09-12-3e4f9d)
  notebook: explore.ipynb
```

`shortest-vs-fewest-dg` is the example used from here on — substitute your own,
as with the snapshot id.

Two files, and git has not been told about either of them yet:

```console
$ ls experiments/shortest-vs-fewest-dg
experiment.toml	explore.ipynb
$ git status
On branch tutorial/dgwartney
Untracked files:
  (use "git add <file>..." to include in what will be committed)
	experiments/shortest-vs-fewest-dg/

nothing added to commit but untracked files present (use "git add" to track)
```

Leave it untracked for now. Step 7 commits the directory once it holds an
answer as well as a question — config, code and results in one reviewable
change.

> **In Colab** — same script treatment as the snapshot:
>
> ```python
> !python scripts/new_experiment.py shortest-vs-fewest-dg \
>     --root experiments --snapshot-root data/snapshots \
>     --snapshot 2026-09-12-3e4f9d \
>     --description "What does it cost to skip a stop?"
> ```
>
> Edit `experiment.toml` from the Files pane on the left — it is a file on the
> runtime's disk like any other.

Open `experiments/shortest-vs-fewest-dg/experiment.toml`. This is what the
scaffolder wrote:

```toml
# shortest-vs-fewest-dg
#
# The snapshot path is relative to this file and resolved against its own
# location, so the experiment travels with the repository. Changing it points
# the experiment at different data -- record a new result if you do.
slug = "shortest-vs-fewest-dg"
description = "What does it cost to skip a stop?"
notebooks = ["explore.ipynb"]
snapshot = "../../data/snapshots/2026-09-12-3e4f9d"  # 2026-09-12-3e4f9d

# Whatever the notebook needs that is not the data itself. Recorded into
# results.json alongside the results, so a run states its own inputs.
[parameters]
origin = "SFO"
destination = "BOS"
```

> **Check the first line.** If it reads `slug = "shortest-vs-fewest"` without
> your suffix, you have opened the finished copy that ships with the
> repository — the one whose parameters are already filled in. Close it and
> open yours.

Note the snapshot path: `../../data/snapshots/…`, relative to this file rather
than to wherever you happen to be standing. That is what lets the clone live
anywhere — including a Colab session — and still find its data.

`origin` and `destination` are the scaffolder's placeholders, and this
experiment asks about three pairs rather than one. **Replace those two lines**
so the bottom of the file reads:

```toml
[parameters]

# Pairs to compare, chosen to span the outcomes: one where the two algorithms
# agree, one where trading a stop costs real distance, and one where it costs
# almost nothing -- but only if you look past what BFS hands back.
pairs = [
    ["SFO", "BOS"],
    ["BOI", "CHS"],
    ["HNL", "BDL"],
]
```

Everything above `[parameters]` stays as it is. Parameters are just values your
code reads; nothing in the library interprets them, and `pairs` is a name this
tutorial chose. They are recorded alongside the results, so a saved answer
always states the inputs that produced it.

---

## Step 5 — Ask the question

The experiment's code can be a notebook **or** a plain Python script. Both read
the same config, verify the same data and write the same `results.json`. So the
choice is not about capability — it is about how you want to work.

**5a — Notebook.** Take it if you want to see each result before writing the next line, and to poke
at the data in between. That is what this step is doing: running a comparison,
noticing a number that looks wrong, and chasing it in Step 6. A notebook is
built for that.

| | |
|---|---|
| The file | `explore.ipynb`, already written by the scaffolder |
| Needs | one more install — `uv sync --group notebooks`, then JupyterLab |
| Run it with | `uv run jupyter lab`, then Shift-Enter, cell by cell |
| Finds itself with | `Path.cwd()` — a notebook's working directory is its own |
| Before committing | clear the outputs, or the test suite fails |
| In Colab | works, with one change — see the box in 5a |

**5b — Script.** Take it if you would rather write the whole thing and run it once, or if you
expect to run it many times — after a data refresh, or in CI, where nobody is
there to press Shift-Enter. It is also the shorter path today: it needs nothing
you did not already install in Step 1.

| | |
|---|---|
| The file | `run.py`, written by the scaffolder with `CODE=run.py` |
| Needs | nothing — Step 1's `uv sync` covered it |
| Run it with | `uv run python …/run.py`, all at once |
| Finds itself with | `Path(__file__).resolve().parent` — a script's working directory is wherever you invoked it |
| Before committing | nothing to do |
| In Colab | the simpler of the two |

**Follow 5a or 5b, not both.** Steps 6 and 7 apply to whichever you chose, and
say what to do in each. Neither is a dead end: the config names the file, so
switching later is a one-line edit.

**Working locally, keep the `uv run` prefix on every command.** It is not
decoration — it runs the command inside the virtual environment `uv sync`
created in Step 1, which is the only place `flight_planner` and pandas are
installed. Drop it and you get a system interpreter that has never heard of
them:

```console
$ python experiments/shortest-vs-fewest-dg/run.py
ModuleNotFoundError: No module named 'flight_planner'
```

> **In Colab** — ignore `uv` entirely, including in the two tables above. You
> installed the package with `pip3` in Step 1, so it is already importable and
> there is no environment to step into: the script route is
> `!python experiments/shortest-vs-fewest-dg/run.py`, and there is no
> JupyterLab to launch, because you are in a notebook already.
>
> **5b is the easier route here.** A script is a file you write into the
> experiment directory with `%%writefile` and run. 5a needs one adjustment,
> described at the top of that section.

---

### Step 5a — The notebook

> **In Colab** — you already have a notebook: the one you are typing in. It is
> not the scaffolded `explore.ipynb`, and it does not live in the experiment
> directory, so the one line that changes is the first:
>
> ```python
> experiment = Experiment.open('/content/traiectoria-optima/experiments/shortest-vs-fewest-dg')
> ```
>
> `Path.cwd()` would be `/content`, which holds no `experiment.toml`, and
> `Experiment.open` raises rather than guessing. Every other cell in this
> section is unchanged. To version what you wrote, see Step 7 — or take 5b,
> where the file is already in the right place.

Install the notebook dependencies and start JupyterLab:

```bash
uv sync --group notebooks     # first time only
uv run jupyter lab
```

Open `experiments/shortest-vs-fewest-dg/explore.ipynb`. The scaffolder wrote a
notebook that runs end to end as it stands — but it was written for the starter
`origin`/`destination` parameters you replaced in Step 4, so **do not run it
top to bottom yet.** Three cells need editing first, and the last of them would
raise `KeyError: 'origin'` if you ran it as it is. Work down the notebook in
order; each cell below depends on the ones above it.

**The import cell**, the first one after the install check, opens the
experiment. A notebook's working directory is the directory it sits in, and it
sits inside the experiment — so `Path.cwd()` is all it needs. The scaffolder
wrote this:

```python
from pathlib import Path

from flight_planner.experiments import Experiment

# The notebook lives in the experiment directory, so the experiment is
# right here. Nothing resolves against a repository root.
experiment = Experiment.open(Path.cwd())
experiment, experiment.parameters
```

Two edits. Add the two algorithms to the imports — the scaffolder does not know
you are going to compare them — and put the pairs in hand for everything below.
Here is the whole cell afterwards:

```python
from pathlib import Path

from flight_planner import BFS, Dijkstra
from flight_planner.experiments import Experiment

experiment = Experiment.open(Path.cwd())
pairs = [tuple(pair) for pair in experiment.parameters['pairs']]
pairs
```

**The cell under "The data"** opens the snapshot, which re-hashes every file
against the manifest — so this cell is also the integrity check. The scaffolder
ends it by displaying the catalog:

```python
snapshot = experiment.snapshot
print(snapshot.snapshot_id, snapshot.criteria)

catalog = experiment.catalog()
catalog
```

Replace that bare `catalog` with a planner and a count. The planner is what the
next cell needs, and it has to be built somewhere:

```python
snapshot = experiment.snapshot
print(snapshot.snapshot_id, snapshot.criteria)

catalog = experiment.catalog()
planner = catalog.planner()
print(f'{len(catalog.routes):,} routes / {len(catalog.airports):,} airports')
```

Run those two cells:

```
2026-09-12-3e4f9d {'airport_type': 'large_airport', 'country': 'US'}
7,005 routes / 94 airports
```

`criteria` is not empty this time — the narrowing happened when you froze the
data, so the notebook does not have to narrow anything. (The other experiment in
this repository does it the other way round, and
[Experiments §6](experiments.md#6-experiment-the-directory-and-its-record)
explains when to choose which.)

The markdown cell between them suggests narrowing the catalog further. Leave it
alone — the narrowing is already in the snapshot — or delete it.

Now **replace the cell under "The question"**, the third and last one that needs
changing, with the comparison. This is the cell that still refers to
`parameters['origin']`, so it is the one that would have raised.
`find_shortest_route` takes the algorithm as its third argument — `Dijkstra`
minimises kilometres, `BFS` minimises legs:

```python
def kilometres(legs):
    """Total distance of a list of legs."""
    return sum(leg.distance_km for leg in legs)


def route_via(origin, legs):
    """Render a route as 'SFO->DEN->BOS'."""
    return '->'.join([origin] + [leg.destination.iata_code for leg in legs])


for origin, destination in pairs:
    by_km, km_legs = planner.find_shortest_route(origin, destination, Dijkstra())
    hops, hop_legs = planner.find_shortest_route(origin, destination, BFS())

    print(f'{origin} -> {destination}')
    print(f'  Dijkstra: {by_km:9,.0f} km  {len(km_legs)} leg(s)  {route_via(origin, km_legs)}')
    print(f'  BFS     : {kilometres(hop_legs):9,.0f} km  {hops:.0f} leg(s)  {route_via(origin, hop_legs)}')
```

Run it with Shift-Enter:

```
SFO -> BOS
  Dijkstra:     4,341 km  1 leg(s)  SFO->BOS
  BFS     :     4,341 km  1 leg(s)  SFO->BOS
BOI -> CHS
  Dijkstra:     3,376 km  3 leg(s)  BOI->DEN->BNA->CHS
  BFS     :     3,531 km  2 leg(s)  BOI->ORD->CHS
HNL -> BDL
  Dijkstra:     8,072 km  3 leg(s)  HNL->SLC->DTW->BDL
  BFS     :     8,616 km  2 leg(s)  HNL->ATL->BDL
```

Then skip past 5b to [Reading the result](#reading-the-result).

---

### Step 5b — The script

No Jupyter, no extra dependency group. You need `run.py` in the experiment
directory, and the scaffolder writes one: `CODE=` names the file, and the
extension picks what goes in it — `.py` a script, anything else a notebook.

**If you passed `CODE=run.py` in Step 4**, it is already there.

**If you took the default and have `explore.ipynb`**, ask for the script now.
`FORCE=1` is needed because the experiment already exists:

```console
$ make experiment SLUG=shortest-vs-fewest-dg SNAPSHOT=2026-09-12-3e4f9d \
      CODE=run.py FORCE=1
experiment: experiments/shortest-vs-fewest-dg
  snapshot: ../../data/snapshots/2026-09-12-3e4f9d (2026-09-12-3e4f9d)
      code: run.py
```

`FORCE=1` regenerates `experiment.toml`, so **re-apply the `[parameters]` edit
from Step 4** — your `pairs` are gone otherwise. Code files are never
overwritten, forced or not; delete `explore.ipynb` if you will not use it.

Either way you now have a starter that opens the experiment, verifies the
snapshot, plans one route and records it — the same steps as the notebook's
cells. **Replace its `main()`** with the comparison, so the file reads:

```python
"""What does it cost to skip a stop? Dijkstra against BFS on three US pairs."""

from pathlib import Path

from flight_planner import BFS, Dijkstra
from flight_planner.experiments import Experiment


def kilometres(legs):
    """Total distance of a list of legs."""
    return sum(leg.distance_km for leg in legs)


def route_via(origin, legs):
    """Render a route as 'SFO->DEN->BOS'."""
    return '->'.join([origin] + [leg.destination.iata_code for leg in legs])


def main() -> int:
    """Compare the two algorithms on every declared pair.

    Returns:
        Process exit status.
    """
    # A script must locate itself: Path.cwd() is wherever you ran it from.
    experiment = Experiment.open(Path(__file__).resolve().parent)
    pairs = [tuple(pair) for pair in experiment.parameters['pairs']]

    # Opening the snapshot re-hashes every file against the manifest.
    snapshot = experiment.snapshot
    print(snapshot.snapshot_id, snapshot.criteria)

    catalog = experiment.catalog()
    planner = catalog.planner()
    print(f'{len(catalog.routes):,} routes / {len(catalog.airports):,} airports')

    for origin, destination in pairs:
        by_km, km_legs = planner.find_shortest_route(origin, destination, Dijkstra())
        hops, hop_legs = planner.find_shortest_route(origin, destination, BFS())

        print(f'{origin} -> {destination}')
        print(f'  Dijkstra: {by_km:9,.0f} km  {len(km_legs)} leg(s)  {route_via(origin, km_legs)}')
        print(f'  BFS     : {kilometres(hop_legs):9,.0f} km  {hops:.0f} leg(s)  {route_via(origin, hop_legs)}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

The one line that differs from the notebook is the `Experiment.open(...)` call.
A script's working directory is wherever you were standing when you ran it, so
it cannot use `Path.cwd()` — it locates itself from `__file__` instead. Get that
wrong and the experiment is looked for in the wrong place; the demo
`src/demos/script_experiment_example.py` shows exactly what that failure looks
like.

> **In Colab** — put the script on disk from a cell by prefixing it with
> `%%writefile`, which has to be the cell's first line, followed by the whole
> script above:
>
> ```python
> %%writefile experiments/shortest-vs-fewest-dg/run.py
> """What does it cost to skip a stop? Dijkstra against BFS on three US pairs."""
> ...
> ```
>
> Then run it with `!python experiments/shortest-vs-fewest-dg/run.py`. Because
> the script locates itself from `__file__`, it does not care that Colab left
> you in `/content` — which is the same reason it works here and on a laptop
> without changing a line.

Run it from anywhere:

```console
$ uv run python experiments/shortest-vs-fewest-dg/run.py
2026-09-12-3e4f9d {'airport_type': 'large_airport', 'country': 'US'}
7,005 routes / 94 airports
SFO -> BOS
  Dijkstra:     4,341 km  1 leg(s)  SFO->BOS
  BFS     :     4,341 km  1 leg(s)  SFO->BOS
BOI -> CHS
  Dijkstra:     3,376 km  3 leg(s)  BOI->DEN->BNA->CHS
  BFS     :     3,531 km  2 leg(s)  BOI->ORD->CHS
HNL -> BDL
  Dijkstra:     8,072 km  3 leg(s)  HNL->SLC->DTW->BDL
  BFS     :     8,616 km  2 leg(s)  HNL->ATL->BDL
```

---

### Reading the result

Both routes print the same three comparisons, because they run the same code
against the same frozen data.

Why `kilometres(hop_legs)` rather than the number BFS returned? Because **the
first value BFS returns is a hop count, not a distance.** It ignores edge
weights entirely — that is what makes it BFS — so it has no kilometres to
report. `find_shortest_route('HNL', 'BDL', BFS())` gives you `2`, not `8616`.
Sum the legs yourself when you want distance.

Read the three results and the story looks clear: `SFO -> BOS` is one leg either
way; `BOI -> CHS` costs 155 km to drop a stop; `HNL -> BDL` costs 544 km.

Except that last number is wrong, and the next step is where you find out.

---

## Step 6 — Check the anomaly

544 km to skip one stop on `HNL -> BDL`, against 155 km on `BOI -> CHS`. Maybe
Hawaii is just awkward. Or maybe BFS is not answering the question we assumed.

**BFS returns the *first* minimum-hop path it finds.** It never compares paths
of equal length, because it never looks at distance at all. So `HNL->ATL->BDL`
is *a* two-leg route, not necessarily the shortest two-leg route.

The catalog can answer what BFS cannot.

> **5a — notebook:** add this as a new cell.
> **5b — script:** put `best_two_leg` beside `kilometres` and `route_via` at
> module level, and the loop at the end of `main()`.

`best_two_leg` takes the catalog as an argument rather than reaching for one
defined elsewhere, so the same code works in a notebook cell and at a script's
module level with nothing changed:

```python
def best_two_leg(catalog, origin, destination):
    """Shortest two-leg route between a pair, by distance."""
    candidates = [
        (first.distance_km + second.distance_km, first.destination.iata_code)
        for first in catalog.routes_from(origin)
        for second in catalog.routes_from(first.destination.iata_code)
        if second.destination.iata_code == destination
    ]
    return min(candidates) if candidates else None


for origin, destination in [('BOI', 'CHS'), ('HNL', 'BDL')]:
    _, hop_legs = planner.find_shortest_route(origin, destination, BFS())
    best_km, hub = best_two_leg(catalog, origin, destination)

    print(f'{origin} -> {destination}')
    print(f'  BFS returned    : {kilometres(hop_legs):9,.0f} km  via {route_via(origin, hop_legs)}')
    print(f'  best two-leg    : {best_km:9,.0f} km  via {hub}')
    print(f'  BFS overshoot   : {kilometres(hop_legs) - best_km:9,.0f} km')
```

```
BOI -> CHS
  BFS returned    :     3,531 km  via BOI->ORD->CHS
  best two-leg    :     3,531 km  via ORD
  BFS overshoot   :         0 km
HNL -> BDL
  BFS returned    :     8,616 km  via HNL->ATL->BDL
  best two-leg    :     8,076 km  via ORD
  BFS overshoot   :       540 km
```

There it is. On `BOI -> CHS`, BFS happened to land on the best two-leg route. On
`HNL -> BDL` it returned one **540 km worse than necessary**, and that overshoot
— not the price of skipping a stop — is what made the pair look expensive.

The real cost of dropping to two legs on `HNL -> BDL` is about **4 km**.

| Pair | Dijkstra | Best at BFS's leg count | Cost of one fewer leg |
|---|---|---|---|
| `SFO`→`BOS` | 4,341 km, 1 leg | — | none |
| `BOI`→`CHS` | 3,376 km, 3 legs | 3,531 km | 155 km |
| `HNL`→`BDL` | 8,072 km, 3 legs | 8,076 km | **4 km** |

Neither algorithm is wrong. They answer different questions, and BFS makes no
promise about *which* of the equally-short-by-legs routes it hands back. If you
want the cheapest route at a fixed number of legs, that is a third question, and
you have to ask it directly — as you just did.

This is the sort of thing that is easy to publish by accident. Which is what the
last step is about.

---

## Step 7 — Record the answer, and commit it

`record()` writes what you found, and refuses to write it without saying where
it came from.

> **5a — notebook:** this is the last cell, already there as
> `experiment.record(...)` — replace its contents.
> **5b — script:** this goes at the end of `main()`, before `return 0`. The
> [appendix](#appendix-a-condensed-one-file-version) is a tidied-up rewrite of
> the same experiment, if you would rather read it whole than assembled.



```python
rows = []
for origin, destination in pairs:
    by_km, km_legs = planner.find_shortest_route(origin, destination, Dijkstra())
    hops, hop_legs = planner.find_shortest_route(origin, destination, BFS())

    row = {
        'pair': f'{origin}-{destination}',
        'dijkstra_km': by_km,
        'dijkstra_legs': len(km_legs),
        'dijkstra_route': route_via(origin, km_legs),
        'bfs_legs': int(hops),
        'bfs_km': kilometres(hop_legs),
        'bfs_route': route_via(origin, hop_legs),
    }

    if len(hop_legs) == 2:
        best_km, hub = best_two_leg(catalog, origin, destination)
        row['best_at_bfs_legs_km'] = best_km
        row['best_at_bfs_legs_via'] = hub
        row['bfs_overshoot_km'] = round(row['bfs_km'] - best_km, 3)
        row['cost_of_one_fewer_leg_km'] = round(best_km - by_km, 3)

    rows.append(row)

experiment.record({'pairs': rows}, catalog=catalog)
```

The dictionary is entirely yours — there is no schema — but note what it
contains: the finding is recorded as *numbers*, not only as prose in a markdown
cell. `bfs_overshoot_km` is 540.118 for `HNL-BDL` and 0.0 for `BOI-CHS`. A
sentence cannot be re-checked automatically; a number can.

Look at what was written — yours will differ in the slug, the timestamp and
the commit it records:

```bash
cat experiments/shortest-vs-fewest-dg/results.json
```

```json
{
  "experiment": "shortest-vs-fewest-dg",
  "recorded": "2026-09-12T01:39:01+00:00",
  "snapshot": {
    "id": "2026-09-12-3e4f9d",
    "reference": "../../data/snapshots/2026-09-12-3e4f9d",
    "criteria": { "airport_type": "large_airport", "country": "US" },
    "source_commit": "4087d45828c2c2e1dde8f59befadde844703b0df"
  },
  "parameters": { "pairs": [["SFO", "BOS"], ["BOI", "CHS"], ["HNL", "BDL"]] },
  "results": { "pairs": [ ... ] },
  "catalog": { "chain": [], "routes": [7005], "airports": [94], "dangling": 0 }
}
```

You wrote the `results` block. Everything else was added for you: which snapshot
the numbers came from, what it was a slice of, which commit produced it, and the
parameters that were in play. `4` km never travels alone.

If you used the notebook, clear its outputs first (**Edit → Clear All
Outputs**) — committed notebooks carry no stored outputs, and a test enforces
it. A script has nothing to clear. Then commit the whole directory:

```bash
git add experiments/shortest-vs-fewest-dg
git commit -m "Ask what a stop costs, and find out BFS overstates it"
```

One commit holds the question, the parameters, the method, the answer, and the
identity of the data. A reviewer can read all five.

> **In Colab** — this is the step that actually differs, because **the runtime
> is disposable.** When the session ends, the clone and everything you wrote
> into it are gone. Get the work out before that happens.
>
> If you took 5a, your code is in the Colab notebook rather than in the
> experiment directory. Clear its outputs (**Edit → Clear all outputs**), then
> **File → Download → .ipynb**, and put the file in
> `experiments/shortest-vs-fewest-dg/` — either by dragging it into the Files
> pane, or in the local clone you commit from.
>
> The runtime has no git identity, so set one before committing:
>
> ```python
> !git config --global user.email "you@example.com"
> !git config --global user.name "Your Name"
> !git -C /content/traiectoria-optima add experiments/shortest-vs-fewest-dg
> !git -C /content/traiectoria-optima commit -m "Ask what a stop costs"
> ```
>
> Pushing needs credentials the runtime does not have. Either push over HTTPS
> with a personal access token, or — simpler, and with nothing secret typed into
> a cell — download `experiments/shortest-vs-fewest-dg/` from the Files pane and
> commit it from a clone on your own machine. The directory is self-contained:
> config, code and `results.json`, with the snapshot named by id inside it.

### Change one thing

Add a pair to `experiment.toml`:

```toml
pairs = [
    ["SFO", "BOS"],
    ["BOI", "CHS"],
    ["HNL", "BDL"],
    ["PDX", "MSY"],
]
```

Re-run it — the notebook or the script, whichever you built — then:

```bash
git diff experiments/shortest-vs-fewest-dg/results.json
```

The diff shows a new pair in `parameters`, a new row in `results` — and an
unchanged `snapshot` block. The inputs moved; the data did not. That is the
whole point of the arrangement: when a number changes, the same commit tells you
whether it was the question, the code, or the data that moved.

Keep it or revert it; the tutorial is done either way.

---

## Compare

`experiments/shortest-vs-fewest/` in this repository is the finished version.
Your `results.json` should carry the same numbers if your snapshot's hash suffix
matched in Step 3. The committed one is also re-run by the test suite, so if the
data ever drifts, the recorded answer is checked against it rather than quietly
going stale:

```bash
uv run pytest tests/experiments/test_committed.py -q
```

## What this skipped

The reference covers each of these:

| Topic | Where |
|---|---|
| Narrowing by airline, international status, and how filters compose | [Experiments §3](experiments.md#3-exploring-the-data-first) |
| Every snapshot filter, and where the airport sizes come from | [Experiments §4](experiments.md#choosing-what-goes-in) |
| What a route with one end in scope and one out should do | [Experiments §5](experiments.md#the-three-endpoint-modes) |
| Dangling edges, and graphs with vertices you did not ask for | [Experiments §5](experiments.md#dangling-edges) |
| Building a small graph by hand from real flights | [Experiments §5](experiments.md#materializing-turning-a-catalog-into-a-graph) |
| Narrowing at freeze time vs in the notebook | [Experiments §6](experiments.md#6-experiment-the-directory-and-its-record) |
| Why `pip install -e` breaks in Colab, and installing without pip at all | [Setup §6](setup.md#6-google-colab) |
| Dijkstra, BFS and A\* in the abstract | [Report §4](report/04-algorithms.md), and Goodrich, Tamassia & Goldwasser ch. 14 |

## Appendix: a condensed one-file version

The same experiment, same data, same recorded numbers — written as one file
someone might keep, rather than as the thing you assembled step by step.

**It is not a transcript of Steps 5b through 7.** The script you built prints
its working as it goes: the snapshot id, the route counts, two lines per pair,
then the anomaly comparison. This one drops all of that in favour of a single
line per pair, because by now the finding is known and the artifact worth
keeping is `results.json`. The `results` block the two write is identical —
that is the part that matters, and the point of the contrast.

Save it as `experiments/shortest-vs-fewest-dg/run.py`, make sure
`experiment.toml` names it in `notebooks`, and run it:

```bash
uv run python experiments/shortest-vs-fewest-dg/run.py
```

In Colab, write it with `%%writefile` and run it with `!python` — the file below
needs no edit for that.

```python
"""What does it cost to skip a stop? Dijkstra against BFS on three US pairs."""

from pathlib import Path

from flight_planner import BFS, Dijkstra
from flight_planner.experiments import Experiment


def kilometres(legs):
    """Total distance of a list of legs."""
    return sum(leg.distance_km for leg in legs)


def route_via(origin, legs):
    """Render a route as 'SFO->DEN->BOS'."""
    return '->'.join([origin] + [leg.destination.iata_code for leg in legs])


def best_two_leg(catalog, origin, destination):
    """Shortest two-leg route between a pair, by distance."""
    candidates = [
        (first.distance_km + second.distance_km, first.destination.iata_code)
        for first in catalog.routes_from(origin)
        for second in catalog.routes_from(first.destination.iata_code)
        if second.destination.iata_code == destination
    ]
    return min(candidates) if candidates else None


def main() -> int:
    """Run the comparison and record it."""
    # A script must locate itself; Path.cwd() is wherever the caller stood.
    experiment = Experiment.open(Path(__file__).resolve().parent)
    catalog = experiment.catalog()
    planner = catalog.planner()

    rows = []
    for origin, destination in experiment.parameters['pairs']:
        by_km, km_legs = planner.find_shortest_route(origin, destination, Dijkstra())
        hops, hop_legs = planner.find_shortest_route(origin, destination, BFS())

        row = {
            'pair': f'{origin}-{destination}',
            'dijkstra_km': by_km,
            'dijkstra_legs': len(km_legs),
            'dijkstra_route': route_via(origin, km_legs),
            'bfs_legs': int(hops),
            'bfs_km': kilometres(hop_legs),
            'bfs_route': route_via(origin, hop_legs),
        }

        if len(hop_legs) == 2:
            best_km, hub = best_two_leg(catalog, origin, destination)
            row['best_at_bfs_legs_km'] = best_km
            row['best_at_bfs_legs_via'] = hub
            row['bfs_overshoot_km'] = round(row['bfs_km'] - best_km, 3)
            row['cost_of_one_fewer_leg_km'] = round(best_km - by_km, 3)

        rows.append(row)
        print(f"{row['pair']:>9}  dijkstra {by_km:8,.0f} km /{len(km_legs)}   "
              f"bfs {row['bfs_km']:8,.0f} km /{row['bfs_legs']}   "
              f"overshoot {row.get('bfs_overshoot_km', 0):>7,.1f} km")

    experiment.record({'pairs': rows}, catalog=catalog)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

```console
  SFO-BOS  dijkstra    4,341 km /1   bfs    4,341 km /1   overshoot     0.0 km
  BOI-CHS  dijkstra    3,376 km /3   bfs    3,531 km /2   overshoot     0.0 km
  HNL-BDL  dijkstra    8,072 km /3   bfs    8,616 km /2   overshoot   540.1 km
```

The `results` block it writes is byte-for-byte what the notebook writes —
same snapshot, same parameters, same narrowing chain, same numbers. The
choice of file type changes nothing about the record.

`src/demos/script_experiment_example.py` is a runnable demo of the same
idea, including what the `Path.cwd()` mistake looks like when it fails.

## See also

- [Experiments](experiments.md) — the same machinery, as a reference
- [Setup](setup.md) — installing `uv`, notebooks, Colab
- [Demos](demos.md) — small runnable scripts, one idea each
- [Makefile](makefile.md) — every target, including `snapshot` and `experiment`
