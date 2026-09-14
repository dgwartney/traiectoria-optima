# Deck

The presentation is built by `make deck` and exported by `make deck-pdf`. It
is **generated from the report chapters** — see
[`docs/report/README.md`](../report/README.md#slides-live-in-the-chapters) for
the authoring format. Editing a slide means editing the chapter it came from.

This directory holds the two things that are not derived:

| File | What it is |
| --- | --- |
| `manifest.txt` | Presentation order. Every chapter slide must be listed; the build fails if one is not, because the alternative is a slide silently missing from the deck. |
| `title.md`, `agenda.md`, `demo.md`, `questions.md` | The deck-only slides. These have no chapter home — no report chapter wants an agenda, and none describes the live demo — so they are written by hand. A file here also *overrides* a chapter slide of the same name, if one ever needs to diverge. |

```sh
make deck            # -> build/html/deck.html
make deck-pdf        # -> build/pdf/deck.pdf, one page per slide
uv run pytest tests/deck
```

## reveal.js comes from a CDN

`deck.html` loads reveal.js from jsDelivr, **pinned to 5.1.0** in the
[`Makefile`](../../Makefile), so the deck cannot shift underneath a rehearsal.
Committing the library instead would put vendored JavaScript in a repository
whose point is from-scratch data structures, which invites the wrong question;
fetching it into `vendor/` at build time worked but cost every clone a setup
step before `make deck` would run at all.

**The consequence is that the built `deck.html` needs a network to present.**
That is what `make deck-pdf` is for: `build/pdf/deck.pdf` embeds everything
and is the offline copy. If you would rather present the HTML with no network,
fetch a local reveal.js and point the build at it:

```sh
make vendor-reveal                 # -> vendor/reveal.js (gitignored)
make deck REVEAL=vendor/reveal.js  # relative URLs, no CDN
```

`--reveal` takes a URL or a directory; a directory is written into the HTML
*relative* to it, so the tree can be copied onto a presentation machine and
still work.

## Neither PDF is committed, and that is the policy

`build/` is gitignored in full, so `build/pdf/deck.pdf` is untracked on exactly
the same terms as `build/pdf/report.pdf`. **The deck is under version control
by virtue of its sources, not its export.** Every input is tracked:

| Input | Where |
| --- | --- |
| Slide content | The `deck-slide` blocks in `docs/report/*.md` |
| Deck-only slides, order | `docs/deck/` |
| Theme | `docs/templates/deck.css` |
| Extraction and dropping | `docs/deck-slides.lua`, `docs/drop-slides.lua` |
| Build and export | `scripts/build_deck.py`, `scripts/export_deck_pdf.py` |
| Figures | `slides/images/*.png`, written by `experiments/route-map` |
| reveal.js | Pinned to 5.1.0 by tag, above |

Committing the PDF would add a binary that cannot be diffed, cannot be
reviewed, and would go stale the moment a chapter changed — reintroducing in
one file the exact drift this whole design exists to prevent. `make deck-pdf`
regenerates it in seconds.

## The slide files under `build/deck/`

`make deck` writes one markdown file per slide there, named by its `id`. They
are build output: the directory is emptied on every build, so an edit made
there is lost. They exist because a single file is far easier to read when a
slide is not laying out the way it should be than a 20-slide HTML document is.
