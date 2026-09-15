"""Generate explore.ipynb for the us-route-map experiment.

Kept beside the notebook so the notebook's own source is reviewable as Python
rather than as JSON, and so regenerating it cannot accidentally leave stored
output behind -- `tests/experiments/test_committed.py` requires every cell's
`outputs` to be empty, and writing the JSON here guarantees it.

Run it from anywhere:

    uv run python experiments/us-route-map/build_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

MARKDOWN: str = "markdown"
CODE: str = "code"

CELLS: List[tuple] = [
    (
        MARKDOWN,
        """# us-route-map

**Who flies where?**

Every other experiment in this repository asks what an *algorithm* does, and
ends in a number. This one asks what the *data* looks like, and ends in a map
you can interrogate: the United States including Alaska, Hawaii and Puerto
Rico, with one switchable layer per airline.

The point is the filtering. Twelve carriers are drawn at once and every one of
them can be switched off independently, so "American against Southwest" or
"who actually reaches Honolulu" is a question the reader answers by clicking
rather than one the author answers for them.

| Layer | What it holds |
|---|---|
| Airports | 473 markers, switched **off** -- at this density they bury the arcs |
| 12 carriers | one `NetworkLayer` each, all switched **on** |
| All other carriers | the pairs the twelve miss, switched **off** |

Nothing here needed new drawing machinery. `flight_planner.viz` was built for
N independent toggleable layers and had only ever been asked for two or three;
the faceting is `Catalog.airline()` for the filter, one `NetworkLayer` per
carrier, and folium's own `LayerControl` for the checkboxes. The one thing that
*was* missing is a carrier colour table, and
[`docs/visualization.md`](../../docs/visualization.md) records what measuring
it changed.

> **Read this map as 2014.** The OpenFlights route table predates a decade of
> consolidation: US Airways and AirTran are the 2nd and 6th largest carriers
> here, and both are marked `[defunct]` in the layer control. `experiment.toml`
> says why they are drawn rather than quietly dropped.

The data is pinned by `experiment.toml` and verified on load: if a byte of the
snapshot changes, this notebook refuses to run rather than reporting different
numbers under the same name.
""",
    ),
    (
        MARKDOWN,
        """## Setup

Only this first cell differs between Colab and a local checkout.

`folium` and `pyproj` are **not** `flight_planner` dependencies -- the wheel
needs pandas and nothing else. They are notebook tools, so a notebook that
draws maps installs them itself. Locally `uv sync --group notebooks` (or
`make notebook`) has already done it.
""",
    ),
    (
        CODE,
        """# In Colab, clone the repository and install the package plus the two
# mapping libraries:
#   !git clone https://github.com/<owner>/traiectoria-optima.git
#   %pip install -q ./traiectoria-optima
#   %pip install -q folium pyproj
# Then open this notebook from the clone.
try:
    import flight_planner  # noqa: F401
except ModuleNotFoundError as error:
    raise SystemExit("install the package first -- see the comment above") from error
""",
    ),
    (
        CODE,
        """import sys
from pathlib import Path

from flight_planner.experiments import Experiment

# The notebook lives in the experiment directory, so the experiment is right
# here. Nothing resolves against a repository root.
HERE = Path.cwd()
sys.path.insert(0, str(HERE))

import plots  # noqa: E402  -- the figure module beside this notebook

experiment = Experiment.open(HERE)
parameters = experiment.parameters

CARRIERS = parameters['carriers']
DEFUNCT = parameters['defunct']
OTHER_LABEL = parameters['other_label']
FOCUS = parameters['focus']
FIGURES = parameters['figures']

len(CARRIERS), DEFUNCT
""",
    ),
    (
        MARKDOWN,
        """## The data

Opening the snapshot re-hashes every file against the manifest.

This slice is `--country US PR --airport-type large medium`. Two things about
it are worth stating, because both are easy to get wrong:

- **Puerto Rico is `PR`, not `US`.** ISO 3166-1 gives it its own code, so
  narrowing on `country("US")` alone silently drops SJU, BQN, PSE, MAZ, VQS
  and CPX -- and with them every Caribbean arc on this map.
- **`large` alone is not enough.** Restricting to large airports leaves Alaska
  as essentially Anchorage by itself, which throws away the bush network that
  is half the reason to draw Alaska.
""",
    ),
    (
        CODE,
        """catalog = experiment.catalog()

# Assert the snapshot is the one this notebook was written for, rather than
# trusting the pinned id. The criteria are restated in experiment.toml.
criteria = experiment.snapshot.criteria
assert criteria['country'] == parameters['countries'], criteria
assert criteria['airport_type'] == [
    f'{kind}_airport' for kind in parameters['airport_types']
], criteria

len(catalog.routes), len(catalog.airports)
""",
    ),
    (
        CODE,
        """from collections import Counter

# Where the airports are. Alaska dominates the count, which is the whole
# argument for keeping medium airports in the slice.
regions = Counter(airport.region for airport in catalog.airports)
offshore = {region: regions[region] for region in plots.OFFSHORE_REGIONS}
offshore, sum(offshore.values()), len(catalog.airports)
""",
    ),
    (
        MARKDOWN,
        """## What each carrier flies

The route table is keyed by flight number, so it holds several rows per city
pair. A map draws one arc per pair, so that is what gets counted here --
`NetworkLayer.distinct_pairs()` does the same collapse one level down, and
counting anything else would report numbers the map does not draw.
""",
    ),
    (
        CODE,
        """counts = plots.carrier_pair_counts(catalog, CARRIERS)
for code, pairs in counts.items():
    print(f'{code:3} {CARRIERS[code]:12} {pairs:>5,}')
print(f'{"":3} {"sum of layers":12} {sum(counts.values()):>5,}')
""",
    ),
    (
        MARKDOWN,
        """### The sum is larger than the network

The twelve layers add up to more arcs than the network has pairs, and that is
not an error -- it is the comparison. A pair flown by both American and Delta
is drawn once in each layer, which is exactly what lets you switch one off and
see whose route it was.

The thirteenth layer holds the pairs *no* named carrier serves, so the
thirteen layers partition the network: in aggregate they cover every pair
exactly once. That makes the bucket's size meaningful -- it answers "how much
of this network do the twelve majors miss?"
""",
    ),
    (
        CODE,
        """union = set()
for code in CARRIERS:
    union |= plots.carrier_pairs(catalog, code)

other = plots.uncovered_routes(catalog, CARRIERS)
network_pairs = {plots.pair_key(route) for route in catalog.routes}

print(f'sum of the twelve layers  {sum(counts.values()):>6,}')
print(f'union of the twelve       {len(union):>6,}')
print(f'pairs they miss           {len(other):>6,}')
print(f'network pairs             {len(network_pairs):>6,}')
assert len(union) + len(other) == len(network_pairs)
""",
    ),
    (
        MARKDOWN,
        """## Who reaches the places a lower-48 map cannot show

This is where restricting to US + PR earns its keep. Alaska, Hawaii and Puerto
Rico each have a different set of carriers, and none of it is visible on a map
of the continental United States.
""",
    ),
    (
        CODE,
        """for region in plots.OFFSHORE_REGIONS:
    leaders = Counter()
    for code in CARRIERS:
        for origin, destination in plots.carrier_pairs(catalog, code):
            if (catalog.airport(origin).region == region
                    or catalog.airport(destination).region == region):
                leaders[code] += 1
    top = ', '.join(f'{code} {n}' for code, n in leaders.most_common(4))
    print(f'{region:8} {top}')
""",
    ),
    (
        MARKDOWN,
        """## The map

One `NetworkLayer` per carrier, each with its own colour and dash, all
switched on. The layer control is the legend -- every label carries the
carrier's route count, the way `PathLayer` labels carry a distance.

Carriers are drawn largest first so the smallest lands on top. Leaflet paints
in insertion order, and Southwest's 570 arcs are invisible under American's
718 if the order is left to chance.
""",
    ),
    (
        CODE,
        """route_map = plots.faceted_map(
    catalog,
    CARRIERS,
    defunct=DEFUNCT,
    other_label=OTHER_LABEL,
)
route_map
""",
    ),
    (
        MARKDOWN,
        """### Four hues, three strokes

Twelve simultaneously distinguishable hues do not exist for a colour-blind
reader, so a carrier's identity is hue **and** stroke -- the same trick a chart
series uses when it carries both a colour and a marker.

The first attempt used six hues and two dash patterns, and measuring it
refuted it: under tritanopia vermillion and reddish purple came out at ΔE 0.9,
indistinguishable, and both were solid. Six hues over two dash classes puts
every hue in every class, so no dash can rescue them. Four hues and three dash
classes fixes it by construction, because each class then holds each hue
exactly once.

`plots.palette_contrast()` is that measurement, and it reports on the pairs
that matter: two carriers a reader must separate by colour alone are two
carriers drawn with the same dash.
""",
    ),
    (
        CODE,
        """contrast = {mode: plots.palette_contrast(mode) for mode in ('light', 'dark')}
for mode, result in contrast.items():
    worst = result['worst_same_stroke']
    floor = min(entry['delta_e'] for entry in worst.values())
    print(f'{mode:6} floor ΔE {floor:5.1f}')
    for view, entry in worst.items():
        print(f'       {view:14} ΔE {entry["delta_e"]:5.1f}  {"-".join(entry["pair"])}')
""",
    ),
    (
        MARKDOWN,
        """## Framing, and the one thing that surprised us

`RouteMap` frames itself on what the layers drew, not on airport positions --
which is what makes a dateline route work. Here nothing crosses ±180, so the
box is well formed, but it is *wide*: Adak in the Aleutians sits at −176.6°
and Culebra off Puerto Rico at −65.3°, 111° of longitude apart. The continental
United States is small in that view.

Worth knowing, and not documented anywhere before this experiment: **a hidden
layer still counts toward the frame.** `bounds()` is the union of what every
layer drew, visible or not, so the switched-off 473-airport layer pins the map
to the full footprint. A single-carrier still comes out as zoomed out as the
whole network until that layer is left out entirely, which is why
`plots.write_stills` omits it for the focus views.
""",
    ),
    (
        CODE,
        """route_map.finish()
bounds = route_map.bounds()
(south, west), (north, east) = bounds

print(f'lat {south:.1f} .. {north:.1f}')
print(f'lon {west:.1f} .. {east:.1f}   ({east - west:.0f} degrees wide)')

# The same map without the hidden airport layer frames on the arcs alone.
arcs_only = plots.faceted_map(catalog, CARRIERS, airports=False)
arcs_only.finish()
print('without the hidden airport layer:', arcs_only.bounds())
""",
    ),
    (
        MARKDOWN,
        """## Output

The interactive HTML is the deliverable, and it is committed -- unusual for
this repository, which keeps generated output out of git and writes
`route-map`'s HTML to a temp directory. The judgement differs here because
interactivity *is* the finding: a map whose point is toggling twelve carriers
cannot be delivered as a still, and one that needs a Jupyter kernel to open is
not delivered at all. It ships under a size bound the tests enforce.

The stills are rendered once and copied, not rendered twice. Screenshot output
is not byte-deterministic -- basemap tiles arrive on their own schedule -- and
`tests/experiments/test_figures.py` requires the two copies to be identical.
""",
    ),
    (
        CODE,
        """interactive = plots.write_interactive(
    route_map, (HERE / FIGURES['interactive'] / 'us-route-map.html').resolve()
)
interactive_bytes = interactive.stat().st_size
print(f'{interactive} {interactive_bytes:,} bytes ({interactive_bytes / 1e6:.2f} MB)')
""",
    ),
    (
        CODE,
        """stills = plots.write_stills(
    catalog,
    CARRIERS,
    FOCUS,
    defunct=DEFUNCT,
    other_label=OTHER_LABEL,
    report_dir=(HERE / FIGURES['report_dir']).resolve(),
    slides_dir=(HERE / FIGURES['slides_dir']).resolve(),
)
for label, paths in stills.items():
    print(f'{label:10} {paths[0].stat().st_size:>8,} bytes')
""",
    ),
    (
        MARKDOWN,
        """## Record

Numbers, not just pictures, so the figures are citable. The per-region
leaders and the palette measurement go in too: the first is what the map is
*for*, and the second is the evidence behind a design decision that a reader
would otherwise have to take on trust.
""",
    ),
    (
        CODE,
        """region_leaders = {}
for region in plots.OFFSHORE_REGIONS:
    leaders = Counter()
    for code in CARRIERS:
        for origin, destination in plots.carrier_pairs(catalog, code):
            if (catalog.airport(origin).region == region
                    or catalog.airport(destination).region == region):
                leaders[code] += 1
    region_leaders[region] = dict(leaders.most_common())

experiment.record(
    {
        'airports_drawn': len(catalog.airports),
        'route_rows': len(catalog.routes),
        'network_pairs': len(network_pairs),
        'carrier_pairs': counts,
        'layer_sum': sum(counts.values()),
        'carrier_union': len(union),
        'other_bucket': len(other),
        'features_drawn': sum(counts.values()) + len(other),
        'airports_by_region': offshore,
        'region_leaders': region_leaders,
        'bounds': {
            'south': south, 'west': west, 'north': north, 'east': east,
            'longitude_span': round(east - west, 1),
        },
        'interactive_bytes': interactive_bytes,
        'palette_contrast': contrast,
    },
    catalog=catalog,
)
experiment.results()['results']['features_drawn']
""",
    ),
]


def notebook() -> Dict[str, Any]:
    """Build the notebook JSON.

    Returns:
        An nbformat 4.5 notebook with no stored output in any cell.
    """
    cells: List[Dict[str, Any]] = []
    for index, (kind, source) in enumerate(CELLS):
        cell: Dict[str, Any] = {
            "cell_type": kind,
            "id": f"cell-{index:02d}",
            "metadata": {},
            "source": source.strip("\n").splitlines(keepends=True),
        }
        if kind == CODE:
            cell["execution_count"] = None
            cell["outputs"] = []
        cells.append(cell)

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.12.12",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    """Write `explore.ipynb` beside this script."""
    destination = Path(__file__).resolve().parent / "explore.ipynb"
    destination.write_text(json.dumps(notebook(), indent=1) + "\n")
    print(f"wrote {destination} ({len(CELLS)} cells)")


if __name__ == "__main__":
    main()
