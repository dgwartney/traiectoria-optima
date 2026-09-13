# Slides

**The in-repo reveal.js deck is retired. The Google Slides deck is the
deliverable.** This directory now holds figures only.

Two decks covered the same ground and only one gets presented. The reveal.js
deck carried 36 `TODO` markers across 31 sections and a Core API slide showing
method names that were never the real API, so maintaining it was waste on the
one deliverable that is behind. The rubric's rule that "a web UI is never
required or rewarded" does not penalise presentation tooling, but it does not
reward it either.

Removed: `index.html`, `css/custom.css`, and the empty `js/`. The last version
of the deck is `7d42b04`, so nothing is lost:

```sh
git show 7d42b04:slides/index.html > /tmp/deck.html   # read the retired deck
git show 7d42b04:slides/css/custom.css                # and its overrides
```

Several design records cite that file by line — `networkx-validation.md`,
`design-search-instrumentation.md` and `evaluation-search-instrumentation.md`
quote its complexity table and its `TODO`s as evidence of what the deck claimed
at the time. Those citations resolve against `7d42b04`, not against this
directory.

## `images/` is live, and is not a deck artifact

The figures stay, and they are written by code rather than by hand:

| Figure | Written by |
| --- | --- |
| `runtime.png`, `nodes-expanded.png` | `experiments/search-cost/plots.py` |
| `degree-distribution.png`, `top-hubs.png` | `experiments/graph-stats/plots.py` |
| `route-map-syd-jfk.png`, `route-map-hnl-bdl.png` | `experiments/route-map/` |

Every experiment renders each figure twice — a dark version here for the deck
and a light version in `docs/images/` for the report — and
`tests/experiments/test_committed.py` asserts both exist. So this directory is
the deck's supply of figures, and deleting it would break the test suite and
the report, not just a retired HTML file.

Put these on the Google deck rather than regenerating them: the comparison
table and the route map are named A1 outcomes, and both are already rendered
here. See [`docs/report-deck-crosswalk.md`](../docs/report-deck-crosswalk.md)
for which report chapter each slide derives from.
