# Slides

Reveal.js deck for the CMPE 180A term project (**A1 — Flight Route Planner**).

Team: Aastha Sharma-Flores, Jake Lu, David Gwartney

## Running

Reveal.js needs to be served over HTTP (the speaker-notes window and `file://`
don't mix). From this directory:

```sh
python3 -m http.server 8000
# then open http://localhost:8000/
```

## Structure

`index.html` is the whole deck. Reveal.js and its `notes` + `highlight` plugins
load from jsDelivr, pinned to 6.0.1 with SRI hashes — if you bump the version,
recompute the hashes or the browser will refuse to load the files:

```sh
curl -sL "https://cdn.jsdelivr.net/npm/reveal.js@<ver>/dist/reveal.js" \
  | openssl dgst -sha384 -binary | openssl base64 -A
```

| Path | Purpose |
| --- | --- |
| `index.html` | the deck |
| `css/custom.css` | overrides on top of the reveal `black` theme |
| `images/` | plots and the route map (referenced, not yet added) |
| `js/` | reserved for any deck-local scripts |

## Conventions

The deck is a **template** — content slides are stubbed and marked so nothing
unfinished ships silently.

- `class="todo"` — yellow, left-barred text. Every one of these must be gone
  before the final presentation.
- `class="placeholder"` — dashed box standing in for a figure, diagram, or table
  we still need to generate.
- `class="cols"` — two-column flex row; wrap two `<div>`s in it.
- `class="chip"` — small pill label.
- `class="small"` / `class="smaller"` / `class="muted"` — text scale and de-emphasis.
- `<aside class="notes">` — speaker notes; press <kbd>S</kbd> for the notes window.

Horizontal sections are top-level topics; nested `<section>`s are vertical
stacks (press <kbd>↓</kbd>). Stage 1–4 each open with a `class="divider"` slide.

## Keys

<kbd>S</kbd> speaker notes · <kbd>O</kbd> or <kbd>Esc</kbd> slide overview ·
<kbd>F</kbd> fullscreen · <kbd>?</kbd> help

To export a PDF, open `http://localhost:8000/?print-pdf` and print from Chrome.

## Remaining work

The narrative scaffold, dataset slide, stage dividers, complexity table, and
reference list are done. Still open: every `todo`/`placeholder` marker, the
architecture diagram, the BFS-vs-Dijkstra-vs-A* results table, the runtime plot,
and the route map.
