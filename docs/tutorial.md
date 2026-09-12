# Tutorial: your first experiment

This walks the whole loop once, end to end: look at the data, freeze the part
you care about, ask a question of it, and record the answer next to the data
that produced it. Half an hour, typing along.

[Experiments](experiments.md) explains the same machinery as a reference. This
is the other order — do it first, understand it second. Every command below is
one you run, and every block of output is real, so you can check yours against
it as you go.

**What you will build.** Your own copy of an experiment called
`shortest-vs-fewest`, asking:

> What does it cost to skip a stop?

A route with the fewest kilometres and a route with the fewest legs are two
different things. We will measure the gap on three pairs of US airports — and
find that one of the three lies to us, for a reason worth knowing.

The finished version already exists here, at
`experiments/shortest-vs-fewest/` — do not peek yet; it is there so you can
compare your numbers against it at the end. Yours will live beside it under a
name of your own, so nothing you do overwrites it.

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

> **Working in Google Colab instead?** The loop is the same, but the setup and
> the paths differ — clone into `/content`, `pip install` rather than `uv sync`.
> [Setup §6](setup.md#6-google-colab) has the install cell, and
> [Experiments §8](experiments.md#8-running-in-colab) shows an experiment opened
> from a Colab clone. Steps 3 and 4 below use `make`, which needs a clone; the
> exploring, asking and recording work anywhere.

---

## Step 2 — Look at the data before freezing any of it

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

Now freeze the slice:

```console
$ make snapshot SNAPSHOT_FILTERS="--airport-type large --country US"
processed: 66332 routes / 3387 airports
  airport_type(large_airport) -> 50474 routes / 1062 airports
  country(US) -> 7005 routes / 94 airports
snapshot: data/snapshots/2026-09-12-3e4f9d
  7005 routes / 94 airports
```

Read that output before scrolling past — it is the only time you are shown it.
The indented lines are your two filters applied one at a time. **They should
end on 7,005 routes and 94 airports, the numbers you saw in Step 2.** If they
do, you froze the scope you meant to.

The last two lines name what was written. `2026-09-12-3e4f9d` is the snapshot's
**id**, and it is also the directory's name.

### Your id will not match mine

An id is `<date>-<content hash>`. You are freezing on a different day, so the
date differs and you get a directory of your own — but **the hash on the end
should be `3e4f9d`**, because that part is computed from the rows themselves.
Same data, same hash, always.

So you will now have two snapshots side by side holding identical rows, mine
and yours. That is expected, and harmless: equal suffixes mean equal data.

If your suffix differs, your processed data is not the same as the data this
tutorial was written against. Nothing is broken; your numbers will simply differ
from the ones printed below.

From here on, substitute your own id wherever you see `2026-09-12-3e4f9d`.

Look at what was written:

```bash
ls data/snapshots/2026-09-12-3e4f9d/
# airports.csv  manifest.json  routes.csv
```

Two CSV files and a manifest recording a SHA-256 checksum for each of them,
plus the narrowing that produced the slice. Commit it:

```bash
git add data/snapshots/2026-09-12-3e4f9d
git commit -m "Freeze the US large-airport network"
```

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

```console
experiment: experiments/shortest-vs-fewest-dg
  snapshot: ../../data/snapshots/2026-09-12-3e4f9d (2026-09-12-3e4f9d)
  notebook: explore.ipynb
```

`shortest-vs-fewest-dg` is the example used from here on — substitute your own,
as with the snapshot id.

Note the snapshot path it recorded: `../../data/snapshots/…`, relative to the
config file rather than to wherever you happen to be standing. That is what
lets the clone live anywhere — including a Colab session — and still find its
data.

Open `experiments/shortest-vs-fewest-dg/experiment.toml` and replace the starter
`[parameters]` with the pairs we want:

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

Parameters are just values the notebook reads; nothing in the library
interprets them. They are recorded alongside the results, so a saved answer
always states the inputs that produced it.

---

## Step 5 — Ask the question

The experiment's code can be a notebook **or** a plain Python script. Both read
the same config, verify the same data and write the same `results.json` — the
only real difference is how each one finds itself on disk.

| | **5a — Notebook** | **5b — Script** |
|---|---|---|
| The file | `explore.ipynb`, already written by the scaffolder | `run.py`, which you create |
| Needs | `uv sync --group notebooks`, JupyterLab | nothing beyond `uv sync` |
| Run it with | Shift-Enter, cell by cell | `uv run python …/run.py` |
| Finds itself with | `Path.cwd()` | `Path(__file__).resolve().parent` |
| Good for | exploring, seeing each result as you go | a settled question, CI, many runs |
| Before committing | clear the outputs | nothing to do |

**Follow 5a or 5b, not both.** Steps 6 and 7 then apply to whichever you chose,
and say what to do in each.

---

### Step 5a — The notebook

Install the notebook dependencies and start JupyterLab:

```bash
uv sync --group notebooks     # first time only
uv run jupyter lab
```

Open `experiments/shortest-vs-fewest-dg/explore.ipynb`. The scaffolder's cells
already do the setup, and they stay as they are.

The first one opens the experiment. A notebook's working directory is the
directory it sits in, and it sits inside the experiment — so `Path.cwd()` is all
it needs:

```python
experiment = Experiment.open(Path.cwd())
pairs = [tuple(pair) for pair in experiment.parameters['pairs']]
```

The next opens the snapshot, which re-hashes every file against the manifest —
so this cell is also the integrity check:

```python
snapshot = experiment.snapshot
print(snapshot.snapshot_id, snapshot.criteria)

catalog = experiment.catalog()
planner = catalog.planner()
print(f'{len(catalog.routes):,} routes / {len(catalog.airports):,} airports')
```

```
2026-09-12-3e4f9d {'airport_type': 'large_airport', 'country': 'US'}
7,005 routes / 94 airports
```

`criteria` is not empty this time — the narrowing happened when you froze the
data, so the notebook does not have to narrow anything. (The other experiment in
this repository does it the other way round, and
[Experiments §6](experiments.md#6-experiment-the-directory-and-its-record)
explains when to choose which.)

Now **replace the cell under "The question"** with the comparison.
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

No Jupyter, no extra dependency group. Two things to do.

**First, tell the config which file is the experiment.** Open
`experiments/shortest-vs-fewest-dg/experiment.toml` and change the `notebooks`
line:

```toml
notebooks = ["run.py"]
```

Nothing checks the extension — `notebooks` is a list of filenames, and a script
is as valid an entry as a notebook.

**Then write the script**, as `experiments/shortest-vs-fewest-dg/run.py`, beside
the config:

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

You can delete `explore.ipynb` if you are not going to use it.

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
> **5b — script:** put `best_two_leg` beside the other helpers at module level
> (it takes `catalog` as an argument there, since it is outside `main()`), and
> the loop at the end of `main()`.

```python
def best_two_leg(origin, destination):
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
    best_km, hub = best_two_leg(origin, destination)

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
> [appendix](#appendix-the-whole-thing-as-a-script) has the finished file if you
> would rather copy it whole.



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
        best_km, hub = best_two_leg(origin, destination)
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

Re-run the notebook, then:

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
| Running all of this in Colab | [Setup §6](setup.md#6-google-colab) |
| Dijkstra, BFS and A\* in the abstract | [Graph Algorithm Notes](graph-algorithms-notes.md) |

## Appendix: the whole thing as a script

The same experiment as a single file, for anyone who took the script route
in Step 5 — or who would rather read it in one piece than as cells. Save it
as `experiments/shortest-vs-fewest-dg/run.py`, make sure `experiment.toml`
names it in `notebooks`, and run it:

```bash
uv run python experiments/shortest-vs-fewest-dg/run.py
```

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
