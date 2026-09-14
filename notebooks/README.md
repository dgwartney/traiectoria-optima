# Notebooks

**Nothing here is a deliverable.** The report's figures and the deck's numbers
come from `experiments/`, where every notebook pins a checksummed snapshot and
writes a committed `results.json`. These two are exploratory scratch, kept for
one reason each.

| File | Why it is still here |
| --- | --- |
| `view_routes.ipynb` | The first map this project drew — `folium.Marker`s in a `FeatureGroup` and one route as a `pyproj` geodesic `PolyLine`. [`docs/visualization.md`](../docs/visualization.md) cites it as the state of play that argued for building `flight_planner.viz`, and lifts its `Geod.npts` call into the great-circle helper. Deleting it would leave that design record pointing at nothing. |
| `folium-groups.ipynb` | A nine-line Folium tutorial about parks and cafés in San Francisco. Cited by the same document, as the other half of "the mapping that exists is exploratory and untransferable". |

Both predate the experiment framework. Both read data directly rather than
through a `Snapshot`, both carry stored output, and both are excluded from
`ruff` (`pyproject.toml`, `extend-exclude`). So a number visible in either one
has **no provenance**, and must not be quoted anywhere — that is precisely the
problem [Appendix F](../docs/report/17-appendix-f-reproducibility.md) §F.1
describes, preserved here as an exhibit rather than fixed.

## What was removed, and why

Three files were retired in the same pass, none of them referenced by any
document, script or test:

- **`airport_data_cleaner.ipynb`** — a pre-framework cleaning pass, superseded
  by `src/data/flight_network.py` and the `data-cleaning` experiment, which
  records all 1,331 dropped routes with a reason each.
- **`great_circle_map.html`** — 147 KB of generated Folium output committed as
  a source file. The current maps are written by `experiments/route-map`.
- **`colab_integration.ipynb`** — a Colab bootstrap that cloned the repository
  and read `data/processed/` directly. [`docs/tutorial.md`](../docs/tutorial.md)
  supersedes it with **In Colab** boxes at every step that needs one, and
  [`setup.md` §6](../docs/setup.md#6-google-colab) explains the install line by
  line — both of which route through a snapshot rather than build output.

## Where the demo notebook will live

The graded demo notebook is tracked as issue #20 and belongs in this directory.
It is held to the experiment rules rather than these: it pins a snapshot, reads
its figures from `experiments/search-cost/results.json` rather than recomputing
them, and carries **no stored output** — which
`tests/experiments/test_committed.py` enforces.
