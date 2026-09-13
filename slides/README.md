# Slides

**Both hand-maintained decks are retired.** The presentation is now built from
the report chapters by `make deck` — see
[`docs/deck/README.md`](../docs/deck/README.md) and
[`docs/report/README.md`](../docs/report/README.md#slides-live-in-the-chapters).
This directory holds figures only.

The history here is two decks and one lesson. The first was an in-repo
reveal.js deck, hand-written; it carried 36 `TODO` markers across 31 sections
and a Core API slide listing method names that were never the real API, so it
was deleted at `b0bb9cf`. The second was Google Slides, chosen because it would
be easier to work on collectively — which did not happen, since one person
built the project. It drifted from the code in nine documented places
(`report-deck-crosswalk.md` §3) and its 12 September export leaked two literal
`TODO` markers onto presented slides.

Both failed the same way: **a deck that is a hand-made copy of the report will
diverge from it.** So the deck stopped being a document. Every content slide is
now a `<div class="deck-slide">` block inside the chapter it summarises, and one
lua filter drops those blocks from the PDF while another keeps only them. There
is one source, and no copy to fall out of date.

The last version of the first deck is `7d42b04`, so nothing is lost:

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

The deck's accent colours come from `src/flight_planner/viz/palette.py`, the
same module these figures are drawn with, so a chart and a bullet on one slide
agree about which colour is Dijkstra.
