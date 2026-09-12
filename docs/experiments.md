# Experiments

An experiment is a question you ask of the flight data — *what is the shortest
route from San Francisco to Boston?* — answered against a locked copy of that
data, with the answer filed next to a note saying which copy it came from.

The locking matters. This project rebuilds its data files regularly, so the
same notebook run next month can quietly give you a different answer, with
nothing to tell you whether the code changed or the data did. An experiment
takes that choice away: it works from a copy that is set in stone, and if so
much as one character of it is altered, it refuses to run rather than handing
back a new number. Come back in a year, run it again, and you either get the
same answer or you find out exactly why not.

This document explains how that works, the three building blocks it is made of,
and how to set up and run an experiment of your own.

**If you would rather learn it by doing it, start with the
[Tutorial](tutorial.md)** — it builds one experiment end to end in half an hour,
and this document is what you read afterwards for the parts it skipped.

The short version:

```python
from pathlib import Path
from flight_planner.experiments import Experiment

experiment = Experiment.open(Path.cwd())      # reads experiment.toml
catalog    = experiment.catalog()             # verifies every checksum
planner    = catalog.airline('UA').planner()  # narrow, then materialize

distance_km, legs = planner.find_shortest_route('SFO', 'BOS')
experiment.record({'shortest_km': distance_km}, catalog=catalog)
```

Four of the [demos](demos.md) cover the same ground end to end, against this
repository's own snapshots:

```bash
uv run python src/demos/snapshot_example.py          # frozen data, and the checksum guarantee
uv run python src/demos/catalog_example.py           # lookup, narrowing, endpoint modes
uv run python src/demos/experiment_example.py        # reading, running and recording one
uv run python src/demos/script_experiment_example.py # an experiment that is a script, not a notebook
```

Every command in this document that starts with `uv run` assumes a clone with
its environment built: install `uv` ([Setup §1](setup.md#1-install-uv)), then
run `uv sync` once in the clone
([Setup §3](setup.md#3-create-the-environment-and-install-dependencies)).
`uv run` then executes the command inside that environment
([Setup §4](setup.md#4-run-things-in-the-environment)) — there is nothing to
activate.

## 1. The problem this solves

The project keeps two kinds of data files. The **raw** ones are downloaded from
outside sources and left alone. The **processed** ones —
`data/processed/airports.csv` and `data/processed/routes.csv`, the clean tables
everything else reads — are not maintained by hand at all: a single command
(`make flight_network`) regenerates them from the raw files and overwrites
whatever was there before. That happens whenever the cleaning steps are
improved, which is often, and the file names never change when it does.

So a notebook that reads those processed files directly has two problems:

- **Re-running it later can produce a different answer**, with nothing to
  indicate that the data moved rather than the code.
- **A number in a report cannot be traced back to the data it came from.**
  "4,341 km" is not a result; "4,341 km, from the frozen copy
  `2026-09-11-bb90a8`, looking only at United's large US airports" is.

The fix is to keep the files that keep changing separate from the copy an
experiment was actually run against — and to make that copy one that cannot be
altered without the change being caught.

## 2. Three pieces

| Class | What it is | You use it to |
|---|---|---|
| `Catalog` | A working set of airports and routes | Explore: look things up, try a smaller slice, see how much of it is left (§3) |
| `Snapshot` | Frozen CSV files plus a manifest of SHA-256 checksums | Freeze the slice you settled on, so it cannot change (§4) |
| `Experiment` | A directory binding code to one snapshot, and its results | Ask a question of that frozen data, and record the answer (§6) |

They are listed in the order you meet them. A catalog is where you work out
what you want; a snapshot makes that choice permanent; an experiment is the
question you then ask of it.

All three ship inside this project's Python package, which means you do not
copy the code around — you install it once and then import it, the same way you
would any other library. How you install it depends on where you are working:

| Where | What you do | Then run things with | Instructions |
|---|---|---|---|
| A clone of this repository | `uv sync` — once, and again after pulling | `uv run python …` | [Setup §3](setup.md#3-create-the-environment-and-install-dependencies) |
| …and for notebooks in that clone | `uv sync --group notebooks` | `uv run jupyter lab` | [Setup §5](setup.md#5-jupyter-notebooks) |
| Google Colab, or any environment that is not this clone | `pip3 install /content/traiectoria-optima` after cloning | plain `python`, or the notebook itself | [Setup §6](setup.md#6-google-colab) |

**In the repository, use `uv`, not `pip`.** `uv sync` reads `pyproject.toml`,
builds a private environment in `.venv/`, and installs this project into it
along with its dependencies, at the exact versions pinned in `uv.lock` —
[Setup §3](setup.md#3-create-the-environment-and-install-dependencies).
Prefixing a command with `uv run` runs it inside that environment, so the
imports resolve without you activating anything —
[Setup §4](setup.md#4-run-things-in-the-environment). If you do not have `uv`
yet, [Setup §1](setup.md#1-install-uv) installs it.

`pip3 install` appears in this document only in the Colab section (§8), where
there is no clone to sync and no `uv`; the install cell is in
[Setup §6](setup.md#6-google-colab).

Two names are involved either way, and they are not the same word.
**`traiectoria-optima`** is the project — the repository's name, the name in
`pyproject.toml`, the name you would see in a package listing.
**`flight_planner`** is what you import — the name the code goes by in Python.
(A project is free to publish under a different name than it imports under, and
this one does.) So every example in this document starts with a line like:

```python
from flight_planner.experiments import Snapshot, Catalog, Experiment
```

Read that line right to left. `flight_planner` is the package; `experiments` is
one section of it — the section about frozen data and recorded results, as
opposed to `flight_planner.pathfinding` (the route-finding algorithms) or
`flight_planner.loaders` (reading CSV files). The dot is just "inside", and the
code for that section lives in `src/flight_planner/experiments/` if you want to
read it.

`Snapshot`, `Catalog` and `Experiment` are the three things you pull out of it,
and they are **Python classes**. A class is a kind of thing the code knows how
to make — a blueprint. Importing one does not give you a snapshot; it gives you
the means to get one. You ask the class for an actual snapshot, and what comes
back is an *instance* of it:

```python
snapshot = Snapshot.open('data/snapshots/2026-09-11-bb90a8')
```

`snapshot` is now one specific frozen dataset, and the dot changes meaning: it
reaches inside that object, for a fact it holds or something it can do.

```python
snapshot.snapshot_id        # a value it holds
snapshot.catalog()          # something it does -- here, hand back a Catalog
```

The parentheses are the difference. `snapshot_id` is read; `catalog()` is
called, and it returns an instance of the next class along — which is why these
three chain together the way the examples show. The capitalised names are the
classes; the lower-case names are the instances you make from them. That is a
convention, not a rule the language enforces, but it holds everywhere in this
project.

To check the environment is working, ask Python:

```bash
uv run python -c "from flight_planner.experiments import Snapshot; print('ok')"
```

Outside the repository, drop the `uv run`.

Being installed is also what shapes the next part. Installed code has no idea
where it ended up: it may be running from a copy of this repository on your
laptop, or from a folder buried somewhere inside a Colab session's Python
installation, with no data anywhere near it.

So none of these three ever goes looking for the data. You tell each one which
folder to use, every time. It reads a little more verbosely in a notebook, and
in exchange the same code works everywhere without a special case for each
place it might be running.

The other half of the story — *creating* snapshots and experiments — does need
to know exactly how this repository is laid out. That code lives in `scripts/`
and is deliberately left out of the installable package.

```
scripts/new_snapshot.py    ->  data/snapshots/<id>/     ->  Snapshot  ->  Catalog
scripts/new_experiment.py  ->  experiments/<slug>/      ->  Experiment
```

## 3. Exploring the data first

Before freezing anything, it is worth looking at what is there. The tool for
that is a **catalog**: a working set of airports and routes that you can look
things up in and narrow down, without changing anything on disk.

This repository ships a frozen copy of the whole network, so you can start
exploring in one line — no pipeline run, no setup:

```python
from flight_planner.experiments import Snapshot

catalog = Snapshot.open('data/snapshots/2026-09-11-bb90a8').catalog()
len(catalog.routes), len(catalog.airports)
# (66332, 3387)
```

### Looking things up

```python
catalog.airport('BOS')                 # one airport
catalog.routes_from('SFO')             # everything leaving SFO
catalog.routes_between('SFO', 'BOS')   # every carrier flying the pair
```

### Narrowing, and seeing how much is left

Narrowing gives you back a smaller catalog, and leaves the one you started with
untouched — so you can try a slice, see how much of the network survives, and
try a different one:

```python
united = catalog.airline('UA')
len(united.routes), len(united.airports)
# (2170, 427)

focused = united.airport_type('large').country('US')
len(focused.routes), len(focused.airports)
# (861, 88)
```

That last line is the answer to a real question — *is 861 routes enough to work
with, or have I cut too deep?* — and you get it in seconds, before committing
to anything. Four narrowings are available: `airline`, `airport_type`,
`country` and `international`. §5 covers them in full, along with `summary()`,
which reports the whole chain step by step.

**This is the design step.** Whatever combination you settle on here is exactly
what you pass to `make snapshot` in §4, under the same names — so exploration
is not a separate exercise from setting up an experiment; it is how you decide
what the experiment should be run against.

### Finding airports, airlines and codes

The data speaks in codes. `SFO` and `BOS` are IATA airport codes, `UA` and `FR`
are IATA airline codes, and `US` is an ISO country code. Nothing lists them for
you up front, so here is how to go from a code to a name, and from a name to a
code.

**A code you have, a name you want.** Airports carry their own description:

```python
airport = catalog.airport('SFO')
airport.name        # 'San Francisco International Airport'
airport.city        # 'San Francisco'
airport.country     # 'US'
airport.type        # 'large_airport'
```

`airport()` is strict — it wants the exact three-letter code and raises if it
does not know it.

Those are the fields every airport carries, and they are what you can search
on:

| Field | Example (`SFO`) | Notes |
|---|---|---|
| `iata_code` | `'SFO'` | The three-letter code; unique, and how everything else refers to an airport |
| `icao_code` | `'KSFO'` | The four-letter aviation code |
| `name` | `'San Francisco International Airport'` | |
| `city` | `'San Francisco'` | The place served, which is not always in the name |
| `country` | `'US'` | ISO 3166-1 |
| `region` | `'US-CA'` | State or province, as ISO 3166-2 |
| `continent` | `'NA'` | `NA`, `SA`, `EU`, `AS`, `AF`, `OC` |
| `type` | `'large_airport'` | The five OurAirports classifications |
| `elevation_ft` | `13.0` | |
| `is_international` | `True` | From the Wikipedia list |
| `has_scheduled_service` | `True` | |
| `wikipedia_link` | `'https://…'` | |

Three of them — `country`, `type` and `is_international` — have narrowing
methods on the catalog, because they are what snapshots slice on. The rest have
no method, and do not need one: `catalog.airports` is an ordinary list, so any
field is one comprehension away.

```python
# By city.
[a.iata_code for a in catalog.airports if a.city == 'Boston']
# ['BOS']

# By continent.
[a for a in catalog.airports if a.continent == 'OC']        # 299 airports

# By state or province.
[a for a in catalog.airports if a.region == 'US-CA']

# Combined, and however you like.
[a for a in catalog.airports
 if a.continent == 'EU' and a.type == 'large_airport' and a.is_international]
```

Filtering this way gives you a plain list of airports. To get a *catalog* back —
one you can narrow further, hand to `planner()`, or freeze — use the narrowing
methods in §5, or pass the codes you found to a comprehension over
`catalog.routes`.

**A name you have, a code you want.** Search the airports for a word you do
know. There is no built-in search, but the list is right there:

```python
def find(text):
    """Airports whose name or city contains `text`."""
    text = text.lower()
    return [airport for airport in catalog.airports
            if text in airport.name.lower() or text in airport.city.lower()]

for airport in find('boston'):
    print(f'{airport.iata_code}  {airport.name}  ({airport.city}, {airport.country})')

# BOS  Boston Logan International Airport  (Boston, US)
# MHT  Manchester-Boston Regional Airport  (Manchester, US)
```

Search the name as well as the city, because the two often disagree — London
Heathrow is `LHR` with city `London`, but plenty of airports are named after a
person or a region rather than the place they serve.

**Which airports actually matter.** If you have no particular airport in mind,
rank them by how much flying they do:

```python
busiest = sorted(catalog.airports,
                 key=lambda a: len(catalog.routes_from(a.iata_code)),
                 reverse=True)[:5]

for airport in busiest:
    print(airport.iata_code, airport.name, len(catalog.routes_from(airport.iata_code)))

# ATL Hartsfield Jackson Atlanta International Airport 915
# ORD Chicago O'Hare International Airport 556
# PEK Beijing Capital International Airport 531
# CDG Charles de Gaulle International Airport 521
# LHR London Heathrow Airport 520
```

**Which codes are worth using.** Ask the data what it holds, and how much:

```python
from collections import Counter
from flight_planner.experiments import Snapshot

catalog = Snapshot.open('data/snapshots/2026-09-11-bb90a8').catalog()

Counter(route.airline for route in catalog.routes).most_common(5)
# [('FR', 2384), ('AA', 2346), ('UA', 2170), ('DL', 1977), ('US', 1960)]

Counter(airport.country for airport in catalog.airports).most_common(5)
# [('US', 613), ('CA', 208), ('CN', 178), ('BR', 126), ('RU', 114)]

Counter(airport.type for airport in catalog.airports).most_common()
# [('medium_airport', 1736), ('large_airport', 1066), ('small_airport', 518),
#  ('heliport', 34), ('seaplane_base', 33)]
```

There are 564 airlines and 230 countries in the full network, so the counts are
the useful part — they tell you which codes are worth filtering on, and roughly
how much data each one will leave you with.

**Turn a code into an airline name.** The codes are terse and several are not
guessable — `FR` is Ryanair, not a French carrier. The raw download the codes
come from carries the names, so search it:

```bash
grep '"UA"' data/raw/open_flights/airlines.dat
# 5209,"United Airlines",\N,"UA","UAL","UNITED","United States","Y"
```

The fields are id, name, alias, **IATA code**, ICAO code, callsign, country,
and whether the airline is still active. To go the other way, search for the
name instead of the code.

**Country codes.** The two-letter codes are ISO 3166-1, the same ones used for
web domains, and the raw data ships the full list with names:

```bash
grep -i '"japan"' data/raw/our_airports/countries.csv
# 302639,"JP","Japan","AS","https://en.wikipedia.org/wiki/Japan","Nippon, ..."
```

The fields are id, **code**, name, continent, Wikipedia link, and search
keywords. Search by name to get a code, or by code to get a name.

Airport types are the one closed list — there are exactly five, and §10 names
them all. Everything else is whatever happens to be in the data.
Once a slice looks right, the next section freezes it.

## 4. Snapshot: data that cannot change quietly

### Making a snapshot, start to finish

Four steps, from a clone of the repository with `uv sync` already run
([Setup §1 and §3](setup.md#1-install-uv)). Each `make` target below is a
wrapper around a `uv run` command, so `uv` does the environment work either
way — see [Makefile](makefile.md).

**Step 1 — make sure the processed data is current.**

```bash
make flight_network
```

This rebuilds `data/processed/airports.csv` and `routes.csv` from the raw
sources. On a fresh clone it always runs, because the stamp file recording
"already built" lives under `.make/` and is not committed. After that it does
nothing unless an input changed, so it is safe to run every time. The rebuild
is deterministic — the same raw files produce the same bytes — so running it
does not move a snapshot you already froze.

**Step 2 — freeze it.**

```bash
make snapshot
```

That takes the whole network. To freeze a slice instead, name the slice you
settled on while exploring in §3 — the filters are the narrowings you already
tried, under the same names, so the catalog that gave you 861 routes and 88
airports there:

```python
catalog.airline('UA').airport_type('large').country('US')
```

is frozen by this:

```bash
make snapshot SNAPSHOT_FILTERS="--airline UA --airport-type large --country US"
```

If you have not explored yet, do that first — it is much easier to settle on a
slice by trying it than by guessing at it. "Choosing what goes in" below is the
full list of filters.

**Step 3 — read the id it prints.** The command prints a report to your
terminal as it runs. Nothing is stored; this is the only time you are shown it,
which is why it is worth reading before you scroll past:

```console
$ make snapshot SNAPSHOT_FILTERS="--airline UA --airport-type large --country US"
processed: 66332 routes / 3387 airports
  airline(UA) -> 2170 routes / 427 airports
  airport_type(large_airport) -> 1661 routes / 256 airports
  country(US) -> 861 routes / 88 airports
snapshot: data/snapshots/2026-09-11-35038d
  861 routes / 88 airports
```

The first line is what it started from. The indented lines are your filters
applied one at a time, each showing what was left afterwards — the same numbers
you saw while exploring, which is a useful check that you froze the slice you
meant to. The last two lines are the result: `data/snapshots/2026-09-11-35038d`
is the folder just written, and `2026-09-11-35038d` is the snapshot's **id** —
the name you will refer to it by from now on.

If you froze exactly this data earlier the same day, you get that same id back
and no new folder — identical data always lands on the same name. The date is
part of the id, though, so freezing the same rows *tomorrow* writes a new
directory whose hash suffix matches today's. Same suffix means same data; keep
whichever you prefer and delete the other.

**If you lose the id**, nothing is broken — it is the folder's name. List the
folders, or ask a snapshot for its own id:

```bash
ls data/snapshots/
# 2026-09-11-1528c4  2026-09-11-35038d  2026-09-11-bb90a8
```

```python
Snapshot.open('data/snapshots/2026-09-11-35038d').snapshot_id
# '2026-09-11-35038d'
```

The same id and the narrowing behind it are also written into the folder's
`manifest.json`, covered under "What is inside a snapshot" below.

**Step 4 — commit it.**

```bash
git add data/snapshots/2026-09-11-35038d
git commit -m "Freeze United's large US airports"
```

**You now have a snapshot.** It is a folder holding two CSV files and a
`manifest.json` that records a checksum for each of them. Point an experiment
at that folder (§6, §7) or open it directly:

```python
from flight_planner.experiments import Snapshot

snapshot = Snapshot.open('data/snapshots/2026-09-11-35038d')
planner  = snapshot.load_planner()
```

From here on, that data is fixed. Every later `Snapshot.open` re-checks the
files against the manifest, so if anyone edits or truncates one of them, the
open fails instead of quietly giving you different numbers.

### Choosing what goes in

With no filters, `make snapshot` freezes the whole network — 66,332 routes
between 3,387 airports. `SNAPSHOT_FILTERS` narrows that down. Five filters are
available:

| Filter | Keeps | Accepts |
|---|---|---|
| `--airline CODE...` | Routes flown by these carriers | Airline codes: `UA`, `AA`, `FR` |
| `--airport-type TYPE...` | Airports of these sizes, and the routes between them | `large`, `medium`, `small`; `heliport` and `seaplane_base` must be written in full |
| `--country ISO...` | Airports in these countries | Two-letter ISO codes: `US`, `GB`, `JP` |
| `--international` | Only airports on Wikipedia's international list | — |
| `--domestic` | Only airports *not* on that list | — |

**Where the airport sizes come from.** `large`, `medium` and `small` are not
measurements this project makes. They are copied straight from the `type`
column of OurAirports' `airports.csv`, one of the raw downloads (see
[Data §5](data.md#5-the-processed-dataset)). OurAirports is community-maintained, and that column is its
contributors' judgement of a field's scale of service — it is not an IATA or
ICAO standard, and it is not computed from runway length or passenger numbers.
Read the three sizes as rough tiers, not thresholds: 1,172 of the world's
airfields are marked `large_airport`, 4,099 `medium_airport` and 42,711
`small_airport`.

The column's full values are `large_airport`, `medium_airport`,
`small_airport`, `heliport` and `seaplane_base`. The first three share the
`_airport` ending, so the bare size is accepted as shorthand — `--airport-type
large` and `--airport-type large_airport` are the same filter, and both record
`large_airport` in the manifest. The other two have no such ending to strip,
so they must be written out in full.

The raw file has two further values, `closed` and `balloonport`. Neither
reaches the network: an airport only appears here if some route touches it, and
nothing scheduled flies to either. That is why §10 lists five types rather than
seven.

**Where "international" comes from.** It is not a property of the flights. The
`is_international` flag is set by scraping Wikipedia's [List of international
airports by
country](https://en.wikipedia.org/wiki/List_of_international_airports_by_country)
and matching those entries against the airport data — 1,329 of the 3,387
airports are on that list. It is an editorial list maintained by Wikipedia's
contributors, so it is neither exhaustive nor authoritative, and it is
independent of size: 116 large airports are absent from it, and 364 medium ones
appear on it. [Data §4](data.md#4-international-airports-scrape-airports_rawjson)
has the scrape in full.

Each one takes as many values as you like, and they mean *any of these*:
`--airline UA AA` keeps both carriers. Use several filters together and they
narrow in sequence, each applying to what the last one left — so
`--airline UA --country US` gives you United's US flying, not United's flying
plus everything American.

How much each filter leaves, measured against the full network:

| `SNAPSHOT_FILTERS` | Routes | Airports |
|---|---|---|
| *(none)* | 66,332 | 3,387 |
| `--airline UA` | 2,170 | 427 |
| `--airline UA AA` | 4,516 | 578 |
| `--airport-type large` | 50,474 | 1,062 |
| `--country US` | 10,702 | 613 |
| `--international` | 44,189 | 1,309 |
| `--domestic` | 3,676 | 1,287 |
| `--airline UA --airport-type large --country US` | 861 | 88 |

Note that the airport counts shrink even when you filter on something that
sounds like it only concerns routes, and vice versa. The two are tied together:
a route is kept only if both of its airports survive, and an airport is kept
only if some surviving route touches it. That is why `--airline UA` leaves 427
airports rather than all 3,387 — the rest are places United does not fly.

That "both of its airports" rule is the default, and it is the one to use unless
you have a specific reason not to. A sixth flag, `--endpoints`, changes it —
useful when you want the flights *out of* a region as well as the ones within
it. It is explained under [the three endpoint modes](#the-three-endpoint-modes),
alongside the same choice as it appears in a notebook.

The filters are the same operations you just used to explore (§3), under the
same names — `--airport-type large` on the command line and
`.airport_type('large')` in Python do the identical thing, which is what lets
you try a slice before you freeze it. If you need to look up a code, §3 shows
how. Whatever you use here is written into the snapshot's manifest, step by
step, so the folder records what it is a slice of.

### What is inside a snapshot

A snapshot is a directory:

```
data/snapshots/2026-09-11-bb90a8/
    airports.csv     3,387 rows
    routes.csv      66,332 rows
    manifest.json
```

The manifest records the id, when it was frozen, the git commit it came from,
the tool that wrote it, the narrowing that produced it, and a SHA-256, byte
count and row count for every file:

```json
{
  "snapshot_id": "2026-09-11-bb90a8",
  "created": "2026-09-11T17:02:13+00:00",
  "source_commit": "610936de75b2d3c45e0e84daea687b32daf35aa3",
  "generator": "scripts/new_snapshot.py",
  "criteria": {},
  "files": {
    "routes.csv": { "sha256": "3450e7a4...", "bytes": 2991700, "rows": 66332 }
  }
}
```

`Snapshot.open()` re-hashes every file and raises `SnapshotIntegrityError` if
one has moved by a single byte. This is not a formality — flipping one bit in
the 3 MB `routes.csv` is detected.

```python
from flight_planner.experiments import Snapshot

snapshot = Snapshot.open('data/snapshots/2026-09-11-bb90a8')
snapshot.snapshot_id        # '2026-09-11-bb90a8'
snapshot.criteria           # {} -- the whole network
snapshot.source_commit      # the commit the data was generated from
snapshot.path('routes.csv') # only files the manifest vouches for
```

Two design points worth knowing:

- **The id is `<date>-<content hash>`.** The suffix is computed from the rows
  themselves, so identical data always produces the same suffix and re-freezing
  the same slice on the same day is a no-op. Different data always produces a
  different suffix, so a changed dataset cannot silently occupy an old id — and
  two snapshots sharing a suffix are byte-identical however far apart they were
  frozen.
- **Verification can be skipped** with `Snapshot.open(directory, verify=False)`,
  which exists because hashing a large snapshot on every open costs real time.
  Skipping it means nothing detects a changed file, so it should be a deliberate
  act, not a default.

### Snapshots in this repository

| Id | Contents | Criteria |
|---|---|---|
| `2026-09-11-bb90a8` | 66,332 routes / 3,387 airports | none — the whole network |
| `2026-09-11-1528c4` | 861 routes / 88 airports | `airline=UA`, `airport_type=large_airport`, `country=US` |

The second predates the pipeline going global and is kept pinned rather than
re-frozen. It is also a working demonstration of forward compatibility: it was
cut before the `is_international` column existed, and it still loads — absent
columns read as their default instead of raising.

## 5. Catalog: the rest of it

§3 introduced catalogs and covered the two things most work needs: looking
airports and routes up, and narrowing the scope. This section is the full
reference — the complete lookup and narrowing vocabulary, the choice that
matters when a narrowing splits a route, and how to turn a catalog into
something you can run algorithms on.

### Lookup

```python
catalog = snapshot.catalog()

catalog.airport('BOS')                 # -> Airport
catalog.flight('UA1876')               # -> Route
catalog.route('SFO', 'BOS', airline='UA')
catalog.routes_between('SFO', 'BOS')   # -> every carrier's leg
catalog.routes_from('SFO')             # -> outgoing only; routes are directed
```

**The flight number is the only unique handle on a route.** SFO to BOS is flown
by three carriers over the identical 4,341.022 km:

```
B60346   UA1876   VX0047
```

So `route('SFO', 'BOS')` cannot answer, and does not guess — it raises and names
the candidates. Pass `airline=`, or use `flight()`.

### Narrowing

Four axes, each returning a new catalog:

```python
catalog.airline('UA')                  # by operating carrier
catalog.airport_type('large')          # by OurAirports size classification
catalog.country('US')                  # by ISO country
catalog.international()                # by the Wikipedia international list
```

Narrowings compose, and every one records what it did:

```python
narrowed = catalog.airline('UA').airport_type('large').country('US')
narrowed.summary()
# {'chain':    [{'operation': 'airline', 'arguments': ['UA'], ...}, ...],
#  'routes':   [66332, 2170, 1661, 861],
#  'airports': [3387, 427, 256, 88],
#  'dangling': 0}
```

That chain is the point. It goes into the snapshot manifest when you freeze a
slice, and into `results.json` when you record a result, so a number always
carries its own derivation.

### The three endpoint modes

A route has two ends. When you narrow by a property of *airports*, you have to
say what happens to a route with one qualifying end and one that does not.

Take a real one. United flight `UA1913` runs San Francisco to Monterey, 124 km:

```python
united = catalog.airline('UA')
leg = united.flight('UA1913')

leg.origin.iata_code,      leg.origin.type        # ('SFO', 'large_airport')
leg.destination.iata_code, leg.destination.type   # ('MRY', 'medium_airport')
```

Now ask for United's large airports. `SFO` qualifies and `MRY` does not, so
`UA1913` is exactly the awkward case — and what happens to it is your choice:

```python
united.airport_type('large', endpoints='both')      # UA1913 dropped; MRY gone
united.airport_type('large', endpoints='either')    # UA1913 kept; MRY comes along
united.airport_type('large', endpoints='airports')  # UA1913 kept; MRY not an airport here
```

- **`both`** — the flight is gone, and so is Monterey. You asked for large
  airports, and this is the strict reading: a network of large airports and the
  flights *between* them.
- **`either`** — the flight survives because one end qualified, and Monterey is
  pulled in with it. Your airport list now holds a medium airport you did not
  ask for. This is the right answer when you want the flying that *reaches*
  large airports, not just the flying between them.
- **`airports`** — the flight survives and Monterey does not. The route now
  points at an airport that is not in your catalog: a **dangling** edge.
  `UA1913` is one of 509 such routes here, between them reaching 170 airports
  that are not in the catalog, and `planner()` will warn you about them.

All three answers are available; none is forbidden.

| `endpoints` | A route is kept when | Consequence |
|---|---|---|
| `"both"` (default) | both ends match | Closed. Order never matters. Nothing dangles. |
| `"either"` | at least one end matches | Keeps hub-to-regional legs; the airport set then contains airports that did not themselves match. |
| `"airports"` | always — routes are untouched | Narrows lookups only. Order matters, and routes can point outside the scope. |

Measured on the full snapshot, starting from `airline('UA')` (2,170 routes /
427 airports) and narrowing to large airports:

| Mode | Routes | Airports | Dangling |
|---|---|---|---|
| `both` | 1,661 | 256 | 0 |
| `either` | 2,144 | 425 | 0 |
| `airports` | 2,170 | 257 | **509** |

`"both"` is the default because it is the only mode that commutes.
`.airline('UA').airport_type('large')` and `.airport_type('large').airline('UA')`
both yield exactly 1,661 routes and 256 airports — the same objects in the same
order — because pruning routes so that both ends qualify and then re-deriving
the airports from what survives makes the order irrelevant.

The other modes are order-dependent, and that is not a defect to be prevented.
The principle here is that the experimenter is **informed, not restricted**: any
narrowing in any order is permitted, and the catalog tells you what it did.

### Dangling edges

`UA1913` above is the case in miniature. Under `endpoints='airports'` the
flight survived but Monterey did not, which leaves the route pointing at an
airport the catalog does not contain. That is a **dangling** edge, and the
catalog will tell you so:

```python
narrowed = united.airport_type('large', endpoints='airports')

'UA1913' in {route.flight_number for route in narrowed.dangling}   # True
'MRY' in set(narrowed.iata_codes)                                  # False

narrowed.airport('MRY')
# KeyError: no airport 'MRY' in this catalog (257 airports in scope)
```

So the scope genuinely does not include Monterey — ask it for `MRY` and it
raises. `narrowed.dangling` is the full list of routes in this position: 509 of
them, reaching 170 airports.

Building a graph from that scope is the interesting part. `planner()` does it
anyway, and warns:

```
509 route(s) reach 170 airport(s) outside this catalog (ABE, ACV, ACY, AEX,
AIA, ...); they are included as vertices. Narrow with endpoints='both' to
avoid this.
```

"Included as vertices" is the thing to notice, and `MRY` is one of them:

```python
planner = narrowed.planner()
any(vertex.iata_code == 'MRY' for vertex in planner.vertices)   # True
```

Monterey is absent from the catalog and present in the graph. It is there
because `UA1913` had to land somewhere — a route cannot be an edge without both
its endpoints — so the graph is not the 257 airports you narrowed to, it is
those plus 170 that arrived attached to surviving flights.

It builds rather than refuses because there are legitimate reasons to want
exactly that graph: routes *out of* a set of airports, with wherever they go
included. It warns because the alternative is a graph whose vertices arrived by
accident — and a shortest path that routes through Monterey when you believed
you were working with large airports only.

### Materializing: turning a catalog into a graph

A catalog is a set of airports and routes. It cannot find you a path — that
needs a *graph*, with airports as vertices and flights as directed edges. Two
methods build one, and both return a `FlightPlanner`, which is what the
pathfinding algorithms take.

**`planner()` — everything in scope.** Every airport becomes a vertex, every
route a directed edge:

```python
from flight_planner import Dijkstra

narrowed = catalog.airline('UA').airport_type('large').country('US')

planner = narrowed.planner()
len(planner.vertices), len(planner.edges)      # (88, 861)

distance_km, legs = planner.find_shortest_route('SFO', 'BOS', Dijkstra())
distance_km                                     # 4341.0
[leg.flight_number for leg in legs]             # ['UA1876']
```

The counts match the catalog exactly — 88 airports, 861 routes — because that
is all `planner()` does: hand the same objects to a graph. The vertices *are*
the catalog's airports, the same instances rather than copies:

```python
planner.vertices[0] is narrowed.airport(planner.vertices[0].iata_code)   # True
```

That identity matters more than it looks. `FlightPlanner` resolves airports by
identity, and an `Airport` hashes on its IATA code alone, so mixing a
catalog-sourced `BOS` with a hand-made `Airport('BOS')` silently keeps one and
discards the other's coordinates — see §9. Anything that comes out of a catalog
is safe by construction; that is the reason to start from one.

**`subgraph()` — only the legs you name.** For building a small network by hand
out of real entities, rather than slicing your way down to one:

```python
planner = catalog.subgraph(['UA1876', 'UA0005'])

[vertex.iata_code for vertex in planner.vertices]   # ['SFO', 'BOS', 'ABQ', 'DEN']
len(planner.edges)                                  # 2
```

Four vertices, because each leg brought its two endpoints along; nothing else
is included, and the two legs are not connected to each other. It takes flight
numbers or `Route` objects interchangeably:

```python
catalog.subgraph([catalog.flight('UA1876'), catalog.flight('UA0005')])
```

and raises rather than guessing if a flight number is not in scope:

```python
catalog.subgraph(['ZZ9999'])
# KeyError: no flight 'ZZ9999' in this catalog (66332 routes in scope)
```

Use it for a worked example, a diagram, or a test — three flights you can hold
in your head, with real coordinates, real distances and real airports, instead
of invented ones that quietly do not behave like the real thing. Use
`planner()` for anything where the answer depends on the whole network.

## 6. Experiment: the directory and its record

You now have frozen data (§4) and a way to work with it (§3, §5). What is
missing is somewhere to put the question and the answer — and, crucially, a
link between the answer and the exact data it came from. That is an experiment.

An experiment is not a class you instantiate or a process you start. **It is a
directory in this repository**, holding three kinds of file:

```
experiments/sfo-bos-dijkstra/
    experiment.toml     what it runs against, and with
    explore.ipynb       the notebook(s) or script(s) -- the question, as code
    results.json        what came out
```

The directory is the unit. It is committed to git, so the question, the
identity of its data, and the answer all move together and are all reviewable
in a diff. Nothing about a result lives only in someone's terminal or in a
notebook's stored output.

The `Experiment` class is the reader for that directory. It resolves which
snapshot the experiment pins, hands you data, and writes results back in a form
that cannot omit where they came from:

```python
from flight_planner.experiments import Experiment

experiment = Experiment.open('experiments/sfo-bos-dijkstra')

experiment.slug              # 'sfo-bos-dijkstra'
experiment.description       # 'Does narrowing the network to one airline ...'
experiment.parameters        # {'origin': 'SFO', 'destination': 'BOS', ...}
experiment.snapshot          # the pinned Snapshot -- checksums verified on open
experiment.catalog()         # a Catalog over it, ready to narrow
experiment.results()         # the last recorded answer, or None
```

`experiments/sfo-bos-dijkstra/` is a real directory in this repository, and the
rest of this section is that experiment's own files.

### The three files

#### `experiment.toml` — what it runs against

The whole configuration is four keys and a table of parameters. This is the
real file, comments trimmed:

```toml
slug = "sfo-bos-dijkstra"
description = "Does narrowing the network to one airline change the shortest SFO-BOS route?"
notebooks = ["explore.ipynb"]
snapshot = "../../data/snapshots/2026-09-11-bb90a8"

[parameters]
origin = "SFO"
destination = "BOS"

# The narrowing under test, as arguments to the catalog.
airline = "UA"
airport_type = "large"
country = "US"

# Further origin/destination pairs the notebook checks, chosen to span the
# outcomes: unchanged, longer, fewer legs, and unreachable.
comparison_pairs = [
    ["SFO", "BOS"],
    ["BOI", "CHS"],
    ["ANC", "BOS"],
    ["HNL", "BDL"],
    ["PWM", "SAN"],
]
```

`slug` names the experiment, `description` states the question in a sentence,
`notebooks` lists the files that answer it, and `snapshot` pins the data.

**The snapshot path is relative to the toml file and resolved against that
file's own location** — never against the working directory, and never by
walking up from `__file__`. This is what lets the repository be cloned anywhere
and the experiment still find its data. An absolute path is also accepted.

`[parameters]` holds whatever the notebook needs that is not the data itself:
an origin, a heuristic, a cutoff. **Nothing in the library interprets them.**
`Experiment` reads the table into a plain dictionary, and the notebook decides
what each key means:

```python
experiment = Experiment.open(Path.cwd())
parameters = experiment.parameters
# {'origin': 'SFO', 'destination': 'BOS', 'airline': 'UA',
#  'airport_type': 'large', 'country': 'US', 'comparison_pairs': [...]}
```

Here is `explore.ipynb` using them, cell by cell. The narrowing under test is
not written into the notebook — it is read out of the config:

```python
narrowed = (
    catalog
    .airline(parameters['airline'])            # 'UA'
    .airport_type(parameters['airport_type'])  # 'large'
    .country(parameters['country'])            # 'US'
)
```

**Wait — isn't that what the snapshot decided?** It can be, and here it
deliberately is not. Narrowing can happen in either place, and which one you
choose is part of designing the experiment:

| Narrow when you… | The frozen data is | Recorded in |
|---|---|---|
| freeze the snapshot (`make snapshot SNAPSHOT_FILTERS=…`) | already the slice | the manifest's `criteria` |
| narrow in the notebook (`catalog.airline(…)`) | the larger set you narrowed *from* | the result's `catalog.chain` |

This experiment pins `2026-09-11-bb90a8`, whose criteria are empty — the whole
66,332-route network — and narrows to United's 861 routes inside the notebook.
It has to. The question is whether narrowing *changes the answer*, so the run
needs both scopes at once: the whole network as the baseline, and the slice to
compare against it. Freeze only the slice and the baseline is gone.

```python
whole = experiment.catalog()                   # 66,332 routes -- as frozen
narrowed = whole.airline('UA')…                #    861 routes -- derived here
```

Freeze the slice instead when every run of the experiment uses it and nothing
needs the wider set — the data is smaller, loads faster, and the manifest
states the scope up front. This repository has one of each:
`2026-09-11-1528c4` is frozen at `airline=UA, airport_type=large_airport,
country=US`, and any experiment pinning it gets those 861 routes with no
narrowing code at all.

Either way the narrowing is recorded, so a result can always be traced to the
scope that produced it. The difference is only whether that record sits in the
snapshot's manifest or in the result's `catalog` block.

The route to measure, likewise:

```python
origin = parameters['origin']                  # 'SFO'
destination = parameters['destination']        # 'BOS'

whole_km, whole_legs = shortest(whole, origin, destination)
slice_km, slice_legs = shortest(narrowed_planner, origin, destination)
```

And the extra pairs drive a loop:

```python
rows = []
for pair_origin, pair_destination in parameters['comparison_pairs']:
    a_km, a_legs = shortest(whole, pair_origin, pair_destination)
    b_km, b_legs = shortest(narrowed_planner, pair_origin, pair_destination)
    rows.append({
        'pair': f'{pair_origin}-{pair_destination}',
        'whole_km': a_km, 'whole_legs': len(a_legs),
        'narrowed_km': b_km, 'narrowed_legs': len(b_legs),
        'extra_km': None if b_km is None else round(b_km - a_km, 1),
    })
```

So `airline = "UA"` in the toml file is what makes `.airline('UA')` happen, and
changing it to `"AA"` re-runs the same experiment against American with no edit
to the notebook. That is the reason to put these values in the config rather
than in the code: the notebook expresses the *method*, the toml file states the
*inputs*, and `record()` copies those inputs into the results so a saved answer
names the settings that produced it.

`comparison_pairs` is a good illustration, because the name means nothing to
the machinery and everything to this experiment. The question here is whether
restricting the network to one airline changes the shortest route. Answering it
for `SFO`→`BOS` alone would be misleading, so the notebook loops over five
origin/destination pairs and compares each one's route on the whole network
against its route on the narrowed one. The pairs were picked to cover the
different things that can happen, and they did:

| Pair | Whole network | Narrowed to United | Outcome |
|---|---|---|---|
| `SFO`→`BOS` | 4,341 km, 1 leg | 4,341 km, 1 leg | unchanged |
| `BOI`→`CHS` | 3,376 km, 3 legs | 3,531 km, 2 legs | 155 km longer, but one leg fewer |
| `ANC`→`BOS` | 5,846 km, 2 legs | 5,959 km, 2 legs | 113 km longer |
| `HNL`→`BDL` | 8,072 km, 3 legs | 8,076 km, 2 legs | barely longer |
| `PWM`→`SAN` | 4,368 km, 2 legs | — | no route at all |

That last row is the one worth having: restricting to a single carrier can
disconnect a pair entirely, which a single well-chosen example would have
hidden. Those numbers are `results.json` below, and the pairs that produced
them are in the parameters — which is the point of recording both.

Parameters are copied into the results, so a recorded run states its inputs as
well as its outputs.

#### `results.json` — what came out

The notebook ends by handing `record()` what it found, along with the catalog it
measured:

```python
experiment.record(
    {
        'pair': f'{origin}-{destination}',
        'whole_network_km': whole_km,
        'whole_network_legs': len(whole_legs),
        'narrowed_km': slice_km,
        'narrowed_legs': len(slice_legs),
        'narrowed_flights': [leg.flight_number for leg in slice_legs],
        'comparison': rows,          # the comparison_pairs table, row by row
    },
    catalog=narrowed,                # the narrowing that produced those numbers
)
```

**The first argument is entirely yours.** There is no results schema, no
required keys, no registry of metric names. Whatever dictionary you pass is
written into the file as the `results` block, verbatim — so the record adapts
to the experiment instead of the experiment contorting to fit the record.

That is what keeps the machinery general. A shortest-path experiment records
distances, leg counts and flight numbers; a timing experiment records
milliseconds per algorithm; a coverage experiment records which airports were
reachable and which were not. None of them need a change to `Experiment`:

```python
experiment.record({'shortest_km': 4341.0, 'legs': 1})

experiment.record({
    'algorithm': 'astar',
    'runs': 100,
    'median_ms': 12.4,
    'per_pair': {'SFO-BOS': 11.8, 'ANC-BOS': 14.1},   # nest as deep as you like
    'notes': 'heuristic admissible for all pairs tested',
})
```

The only rule is that it has to be JSON. Strings, numbers, booleans, `None`,
lists and dictionaries nest freely; anything else raises `TypeError` and
nothing is written:

```python
experiment.record({'airport': catalog.airport('SFO')})
# TypeError: Object of type Airport is not JSON serializable

experiment.record({'airport': catalog.airport('SFO').iata_code})   # 'SFO' -- fine
```

Pull out the value you want rather than storing the object: a code, a number, a
list of flight numbers. Watch for numpy in particular — `np.float64` happens to
serialize because it subclasses `float`, but `np.int64` and arrays do not, so
convert with `int(…)` or `.tolist()` before recording.

Everything *around* that block is added for you, and that is the other half of
the point: **`record()` will not write a result that does not say where it came
from.**

The file it writes has five blocks, and you have met all five already:

| Block | What it holds | Where it came from |
|---|---|---|
| `experiment`, `recorded` | Slug and a UTC timestamp | The directory's identity |
| `snapshot` | Id, path, criteria, source commit | The snapshot pinned in `experiment.toml` (§4) |
| `parameters` | Every key from `[parameters]` | The toml file, copied verbatim |
| `results` | Whatever you passed to `record()` | The notebook |
| `catalog` | The narrowing chain and its counts | The `catalog=` argument — `narrowed.summary()` |

Here is the real file, with the long lists trimmed:

```json
{
  "experiment": "sfo-bos-dijkstra",
  "recorded": "2026-09-11T17:03:30+00:00",
  "snapshot": {
    "id": "2026-09-11-bb90a8",
    "reference": "../../data/snapshots/2026-09-11-bb90a8",
    "criteria": {},
    "source_commit": "610936de75b2d3c45e0e84daea687b32daf35aa3"
  },
  "parameters": {
    "origin": "SFO", "destination": "BOS",
    "airline": "UA", "airport_type": "large", "country": "US",
    "comparison_pairs": [["SFO", "BOS"], ["BOI", "CHS"], ["ANC", "BOS"],
                         ["HNL", "BDL"], ["PWM", "SAN"]]
  },
  "results": {
    "pair": "SFO-BOS",
    "whole_network_km": 4341.022084519025, "whole_network_legs": 1,
    "narrowed_km": 4341.022084519025,      "narrowed_legs": 1,
    "narrowed_flights": ["UA1876"],
    "comparison": [
      { "pair": "SFO-BOS", "whole_km": 4341.0, "whole_legs": 1,
        "narrowed_km": 4341.0, "narrowed_legs": 1, "extra_km": 0.0 },
      { "pair": "BOI-CHS", "whole_km": 3376.0, "whole_legs": 3,
        "narrowed_km": 3531.4, "narrowed_legs": 2, "extra_km": 155.4 },
      { "pair": "PWM-SAN", "whole_km": 4368.0, "whole_legs": 2,
        "narrowed_km": null,  "narrowed_legs": 0, "extra_km": null }
    ]
  },
  "catalog": {
    "chain": [
      { "operation": "airline",      "arguments": ["UA"],             "routes": [66332, 2170] },
      { "operation": "airport_type", "arguments": ["large_airport"],  "routes": [2170, 1661] },
      { "operation": "country",      "arguments": ["US"],             "routes": [1661, 861] }
    ],
    "routes":   [66332, 2170, 1661, 861],
    "airports": [3387, 427, 256, 88],
    "dangling": 0
  }
}
```

Read across the blocks and the whole story is there:

- `comparison` is the table from earlier in this section, one object per pair —
  including `PWM-SAN` with `"narrowed_km": null`, the pair United cannot fly.
  The pairs that produced those rows are two blocks up in `parameters`.
- `catalog.chain` is the narrowing the notebook performed, step by step:
  66,332 routes → 2,170 → 1,661 → 861. Those are the same numbers §3 printed
  while exploring, now written down permanently.
- `snapshot.criteria` is `{}`, which says the frozen data was the *whole*
  network — so the narrowing in `chain` happened in the notebook, not at freeze
  time. A reader can tell the two apart without asking anyone.
- `snapshot.id` and `source_commit` identify the bytes and the code that
  produced them.

So "4,341 km" never travels alone. It travels with the airline that was
selected, the pairs it was compared against, the four scopes the narrowing
passed through, and the checksummed dataset underneath — which is what §1 said
a result needs to be.

**The guarantees.** `record()` opens the snapshot before writing, and opening
verifies every checksum, so recording against altered data raises
`SnapshotIntegrityError` instead of writing a result that claims to come from
data that no longer exists. The payload is serialized to JSON before the file
is touched, so a result containing something JSON cannot represent leaves the
previous run intact rather than truncating it. And a previous run is replaced
rather than appended to — git holds the history, so the file holds the current
answer.

**Notebooks are committed without stored outputs.** Outputs are re-derivable,
they make diffs unreadable, and `results.json` is the recorded answer. A test
enforces this.

### It does not have to be a notebook

`notebooks` in `experiment.toml` is a list of filenames. Nothing checks the
extension, and nothing requires the files to exist when the experiment is
opened — so a plain Python script works just as well. The scaffolder will write
one for you:

```bash
make experiment SLUG=script-experiment CODE=run.py
```

What it produces is the shape below — the same steps as the starter notebook,
in a file that locates itself:

```toml
slug = "script-experiment"
notebooks = ["run.py"]
snapshot = "../../data/snapshots/2026-09-12-3e4f9d"
```

```python
"""An experiment as a plain script."""
from pathlib import Path

from flight_planner import Dijkstra
from flight_planner.experiments import Experiment


def main() -> int:
    # A script knows where it lives; it must not rely on the caller's cwd.
    experiment = Experiment.open(Path(__file__).resolve().parent)
    planner = experiment.catalog().planner()

    rows = []
    for origin, destination in experiment.parameters["pairs"]:
        km, legs = planner.find_shortest_route(origin, destination, Dijkstra())
        rows.append({"pair": f"{origin}-{destination}", "km": km, "legs": len(legs)})

    experiment.record({"pairs": rows}, catalog=experiment.catalog())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

That runs from anywhere — `uv run python experiments/<slug>/run.py` — and
produces exactly the same `results.json`, with the same verified checksums and
the same recorded narrowing chain. Everything else in this section applies
unchanged; only the file type differs.

One thing does change. A notebook can call `Experiment.open(Path.cwd())`,
because a notebook's working directory is the directory it sits in. **A script
cannot** — its working directory is wherever the caller happened to be. Use
`Path(__file__).resolve().parent` instead, as above, or the experiment will be
looked for in the wrong place.

Two smaller differences:

- `make experiment` always scaffolds a notebook. Choosing a script means writing
  it yourself and naming it in `notebooks`.
- The stripped-outputs rule is about notebooks specifically. A script has no
  stored output to strip, and the test skips anything that is not an `.ipynb`.

Use a notebook when the work is exploratory and the narrative matters — which is
what most experiments here are. Use a script when the question is settled and you
want it runnable in one command, in CI, or across many parameter sets. The
`notebooks` list can hold both.

A runnable version of all of this, including what the `Path.cwd()` mistake looks
like when it fails:

```bash
uv run python src/demos/script_experiment_example.py
```

### Experiments in this repository

Three are committed, and they are worth reading in this order — each one adds
something the previous did not need.

| Slug | Question it asks | Snapshot | What it adds |
|---|---|---|---|
| [`sfo-bos-dijkstra`](../experiments/sfo-bos-dijkstra) | Does narrowing the network to one airline change the shortest SFO–BOS route? | `2026-09-11-bb90a8` — 3,387 airports / 66,332 routes, no criteria | The baseline shape. Pins the whole world and narrows **inside the notebook**, so the narrowing is part of the question. |
| [`shortest-vs-fewest`](../experiments/shortest-vs-fewest) | What does it cost to skip a stop? Dijkstra against BFS on three US pairs. | `2026-09-12-3e4f9d` — 94 airports / 7,005 routes, US large airports | The opposite choice: narrowed at **freeze** time, so the notebook narrows nothing. The [Tutorial](tutorial.md) builds this one end to end. |
| [`search-cost`](../experiments/search-cost) | How much cheaper is informed search? BFS, Dijkstra and A\* on the world network. | `2026-09-11-bb90a8` — the whole world | Measures **time**, so it records the machine alongside the numbers, fits a growth exponent per series, and ships its own `plots.py` writing figures the deck and the report consume. |

`search-cost` is the one to copy if your experiment measures *time*. The other
two record answers, which reproduce anywhere; a timing only means something
alongside the CPU it ran on, so that experiment records `environment` — CPU
model, core count, platform, Python version, and whether it was a Colab
runtime. Growth exponents and node counts are portable; milliseconds are not.

## 7. Creating snapshots and experiments

Two commands, and between them they produce everything the previous sections
described.

```bash
make snapshot                                    # freeze the whole network
make snapshot SNAPSHOT_FILTERS="--airline UA"    # freeze a slice
make experiment SLUG=astar-heuristics            # scaffold an experiment
```

### More about `make snapshot`

§4 walked through freezing one. Three things it did not say:

**Rows are carried across verbatim.** Every column is read as text and written
back untouched, so a snapshot's bytes are the processed file's bytes for the
rows that survived. No re-formatted floats, no `1.0` becoming `1`, no drift
between what the pipeline produced and what you froze.

**Re-freezing identical data is free, within the day.** The id is
`<date>-<content hash>`, so running `make snapshot` twice with the same filters
writes nothing the second time — it reports the id that already exists. Across
days the hash still matches but the date does not, so you get a second
directory holding identical rows. That is harmless and easy to spot: equal
suffixes mean equal data, so delete whichever copy nothing pins.

**The filters are the catalog's.** `--airline UA` is `catalog.airline('UA')`,
with the same normalization and the same endpoint rules, which is why §3's
exploration numbers and §4's frozen counts agree. The full list is in
[Choosing what goes in](#choosing-what-goes-in); every option is in
`uv run python scripts/new_snapshot.py --help`.

### `make experiment` — scaffolding a new one

Writing `experiment.toml` by hand is easy to get subtly wrong: the snapshot
path has to be relative to the file rather than to wherever you happen to be
standing. The scaffolder handles that, and gives you a notebook that already
runs.

```console
$ make experiment SLUG=astar-heuristics
experiment: experiments/astar-heuristics
  snapshot: data/snapshots/2026-09-11-bb90a8 (2026-09-11-bb90a8)
  notebook: explore.ipynb
```

That creates two files:

```
experiments/astar-heuristics/
    experiment.toml     pinned to a snapshot, with a starter [parameters]
    explore.ipynb       four code cells that run end to end as written
```

`results.json` is not created — it appears the first time the notebook calls
`record()`.

**Which snapshot it pins.** With no `SNAPSHOT=`, the most recent one, chosen by
the manifest's `created` timestamp rather than by directory name — ids sort
arbitrarily within a day. Name one explicitly to pin something older:

```bash
make experiment SLUG=astar-heuristics SNAPSHOT=2026-09-11-1528c4
```

The path is written relative to the experiment directory
(`../../data/snapshots/…`), which is what lets the clone live anywhere. An
experiment created outside the repository gets an absolute path instead.

**What is in the starter notebook.** Not a placeholder — this is the whole
thing, and it runs as written. Four code cells and the markdown between them.

It opens with a title, your `--description`, and a note on what the pinning
buys you. Then a setup cell whose only job is to fail clearly if the package is
missing, and to carry the Colab instructions as a comment:

```python
# In Colab, clone the repository and install the package first:
#   !git clone https://github.com/<owner>/traiectoria-optima.git
#   %pip install -q ./traiectoria-optima
# Then open this notebook from the clone.
try:
    import flight_planner  # noqa: F401
except ModuleNotFoundError as error:
    raise SystemExit("install the package first -- see the comment above") from error
```

Next, the experiment opens itself. The notebook lives *inside* the experiment
directory, so the current working directory is the experiment — no repository
root to locate, no paths to configure:

```python
from pathlib import Path

from flight_planner.experiments import Experiment

experiment = Experiment.open(Path.cwd())
experiment, experiment.parameters
```

Then the data. Opening the snapshot re-hashes every file against the manifest,
so this cell is also the integrity check:

```python
snapshot = experiment.snapshot
print(snapshot.snapshot_id, snapshot.criteria)

catalog = experiment.catalog()
catalog
```

A markdown cell follows showing how to narrow, in case the experiment works on
part of the network — it is a prompt, not code that runs:

```python
catalog = catalog.airline('UA').airport_type('large')
catalog.summary()
```

Under the heading **The question** is the cell you are meant to replace. As
generated it finds a shortest route between the `origin` and `destination` in
`[parameters]`:

```python
planner = catalog.planner()

origin = experiment.parameters['origin']
destination = experiment.parameters['destination']
distance_km, legs = planner.find_shortest_route(origin, destination)

print(f'{distance_km:,.1f} km in {len(legs)} leg(s)')
for leg in legs:
    print(f'  {leg.flight_number}  {leg.origin.city} -> {leg.destination.city}')
```

And under **The answer**, the recording cell — note `catalog=catalog`, which is
what puts the narrowing chain into `results.json`:

```python
experiment.record(
    {
        'shortest_km': distance_km,
        'legs': len(legs),
        'flights': [leg.flight_number for leg in legs],
    },
    catalog=catalog,
)
```

Run all cells and you have a real `results.json`, traceable end to end, before
you have written a line. From there: replace the question cell, extend the
recorded dictionary, add parameters as you find things worth varying, and
delete the narrowing prompt if you do not need it.

**Re-running the scaffolder is safe.** It refuses rather than overwriting:

```console
$ make experiment SLUG=astar-heuristics
experiments/astar-heuristics/experiment.toml already exists; pass --force to overwrite it
```

`--force` regenerates the config the script owns and **never** touches a
notebook — that is your work. Use it to re-point an experiment at a different
snapshot without losing anything you have written.

```bash
uv run python scripts/new_experiment.py --help
```

### Then what — it is just git

Yes: an experiment is ordinary files in the repository, and you work with them
the way you work with any other files. There is no experiment server, no
registry, no database, nothing to sync. `git add`, `git commit`, branch, review,
merge, revert.

```bash
git add experiments/astar-heuristics
git commit -m "Ask whether A* changes the answer on the full network"
```

What the design buys you is that normal git habits do the right thing, because
everything an answer depends on is in the same commit as the answer:

- **A diff shows a changed result *and* what changed about it.** If
  `results.json` moves, the same commit shows whether the notebook, the
  parameters or the pinned snapshot moved with it. A result that changed with
  nothing else touched means the *code* changed, and that is worth knowing.
- **`git log -p experiments/astar-heuristics/results.json`** is the history of
  the answer. `record()` replaces rather than appends precisely so the file
  holds today's answer and git holds every previous one.
- **Branching works how you would hope.** Try a different narrowing on a
  branch, record, compare the two `results.json` files, keep the branch you
  believe. Reverting a commit reverts the question, the inputs and the answer
  together.
- **Review is possible at all.** A reviewer reads a small TOML file, a notebook,
  and a JSON file that names its own snapshot — rather than being asked to
  trust a number pasted into a message.

Two habits differ from ordinary notebook work, and both are enforced by
`tests/experiments/test_committed.py`:

**Notebooks are committed with their outputs stripped.** A notebook carrying
stored outputs turns every run into a huge unreadable diff, and it invites a
reader to trust rendered numbers that nothing verified. `results.json` is the
recorded answer; the notebook is the method. The test walks every cell of every
committed notebook and fails if any of them has `outputs`.

**Snapshots are committed too, and they are data.** The full network is 3.4 MB,
the United slice 64 KB. That is the price of a result you can re-derive a year
later, and it is why snapshots are deduplicated by content hash rather than
re-frozen on a whim.

The same test suite also re-runs the committed experiment and checks that the
recorded narrowing still narrows the same way and the recorded answer is still
the answer. So "it is just git" comes with a safety net: if the pipeline, the
catalog or the loaders drift, CI notices that a committed result no longer
matches the data it claims to come from.

### Plotting, mapping and anything else a notebook does

It is a notebook. Import `matplotlib`, `folium`, `seaborn`, whatever you like —
nothing about an experiment restricts what runs inside one. The catalog hands
you domain objects with real coordinates, so plotting is direct:

```python
import matplotlib.pyplot as plt

narrowed = catalog.airline('UA').airport_type('large').country('US')

fig, ax = plt.subplots(figsize=(8, 5))
for route in narrowed.routes:
    ax.plot([route.origin.longitude, route.destination.longitude],
            [route.origin.latitude, route.destination.latitude],
            linewidth=0.3, alpha=0.5)
ax.scatter([airport.longitude for airport in narrowed.airports],
           [airport.latitude for airport in narrowed.airports], s=8)
ax.set_title(f'United, large US airports — {len(narrowed.routes)} routes')
```

Where those libraries come from depends on where you are working — the same
split as §2:

| | Plotting |
|---|---|
| **In a clone** | `matplotlib` comes with `uv sync` (it is in the `dev` group). The mapping libraries — `folium`, `ipyleaflet`, `pyproj` — need `uv sync --group notebooks` ([Setup §5](setup.md#5-jupyter-notebooks)). |
| **In Colab** | Nothing to do. `matplotlib`, `seaborn`, `folium` and `plotly` are preinstalled; `uv` is not involved at all. |

`notebooks/` in this repository has worked examples of both the chart and the
map cases.

**When the figure is a deliverable, give it a module.**
[`experiments/search-cost/plots.py`](../experiments/search-cost/plots.py) is the
pattern: chart code in a module beside the notebook, imported by it, and covered
by its own test (`tests/experiments/test_search_cost_plots.py`). Three reasons it
beats drawing inline, all of which came up building it:

- **The same chart is needed on two surfaces.** The reveal.js deck is dark, the
  pandoc report is light. One function with a `mode="dark"|"light"` argument
  renders both from one definition, instead of two copies that drift.
- **It writes where the consumer already looks** — `slides/images/runtime.png`
  and `docs/images/runtime-light.png`, not the experiment directory, because
  that is where the deck and the report reference them from.
- **Chart code is testable; a notebook cell is not.** The test drives both
  functions on the recorded results in both modes, which catches a chart that
  stopped rendering without anyone opening a PNG.

Keep the module out of `flight_planner` itself. The wheel depends on `pandas`
alone, and `matplotlib` is a `dev`-group dependency — plotting is something this
repository does, not something the package offers.

**One wrinkle: committed notebooks carry no stored outputs**, so a chart drawn
inline vanishes from the committed file. It re-draws when someone runs the
notebook, which is usually fine. When a figure is itself a deliverable, save it
next to the experiment and commit the file:

```python
fig.savefig(experiment.directory / 'network.png', dpi=150, bbox_inches='tight')
```

Then reference it from the notebook or a README in the experiment directory —
the figure is versioned like everything else, and a reviewer sees it without
running anything.

**Record the numbers, not just the picture.** A chart is for a human reading the
notebook; `results.json` is what another run compares against. If a plot shows
that narrowing adds 155 km on one pair, put that 155 in `record()` too — an
image cannot be diffed, and a number can.

## 8. Running in Colab

See [Setup §6](setup.md#6-google-colab) for the install cell, and the
[Tutorial](tutorial.md#in-colab-instead) to walk the whole loop — freeze,
scaffold, run, record — inside a Colab session. Once the package is installed
and the repository cloned, an experiment is three lines:

```python
from flight_planner.experiments import Experiment

experiment = Experiment.open('/content/traiectoria-optima/experiments/sfo-bos-dijkstra')
planner    = experiment.snapshot.load_planner()   # checksums verified here
experiment.record({'shortest_km': 4341.0, 'legs': 1})
```

This was verified end to end from a clean clone, running under the installed
wheel from an unrelated working directory, with Colab's pinned pandas 2.2.3 and
numpy 2.1.3 left untouched.

To version a notebook written in Colab, commit from the clone — the experiment
directory is a normal part of the repository.

## 9. Things to know before you rely on this

**Flight numbers are assigned, not real.** `UA1876` is not a published United
flight. The numbers are generated by the pipeline as `{airline}{n:04d}`, ordered
by `(source, destination)`, so that every route has a stable unique handle.
`(airline, source, destination)` is unique across all 67,663 raw routes, so the
assignment is collision-free. Do not present them as real schedules.

**Numbering leaves gaps, deliberately.** Numbers are assigned to the *raw* route
set, before endpoint resolution. United is numbered `UA0001`–`UA2180` but ships
2,170 rows, because 10 of its routes reference airports with no usable IATA code
or coordinates. The alternative — numbering after resolution — would renumber
every downstream route the moment an entry was added to
`data/reference/iata_code_overrides.csv`. Stability was judged worth the gaps.

**1,331 of 67,663 raw routes are dropped** (98.0% resolve), referencing airports
that no longer exist or have been renamed (TXL, SXF, TSE). The pipeline reports
them rather than dropping them silently.

**`Airport` hashes on IATA code alone, and `Graph.add_vertex` is first-wins.**
Mixing a bare `Airport('BOS')` with a catalog-sourced BOS keeps whichever was
added first and silently discards the other's coordinates — which would make
A\*'s Haversine heuristic measure from (0, 0). Entities that come from a catalog
are safe by construction. This is documented and tested rather than fixed,
because changing it would change core graph semantics.

**`international` is not a synonym for `large`.** The flag comes from
Wikipedia's list of international airports and is independent of the OurAirports
size classification: 116 large airports are absent from that list, and 364
medium ones appear on it.

## 10. Reference: the full network

From `data/snapshots/2026-09-11-bb90a8`:

| | |
|---|---|
| Routes | 66,332 (of 67,663 raw; 98.0% resolve) |
| Airports | 3,387 — only those a route touches, from 9,053 with a usable IATA code |
| Airlines | 564 (568 raw) |
| Countries | 230 |
| Continents | 6 |

Airports by `type`:

| Type | Count |
|---|---|
| `medium_airport` | 1,736 |
| `large_airport` | 1,066 |
| `small_airport` | 518 |
| `heliport` | 34 |
| `seaplane_base` | 33 |

Note there are **five** classifications, not three — `airport_type('large')`,
`('medium')` and `('small')` are shorthand for the `_airport` forms, but
heliports and seaplane bases must be named in full.

Busiest carriers by resolved routes: `FR` 2,384 · `AA` 2,346 · `UA` 2,170.

1,329 of the 3,387 airports are listed as international.

## See also

- [Setup](setup.md) — installing, and the Colab install cell
- [Data](data.md) — where the raw data comes from and what the pipeline makes of it
- [Makefile](makefile.md) — every target, including `snapshot` and `experiment`
