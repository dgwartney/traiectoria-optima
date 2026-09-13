# Final Report — chapters

The final report is split one file per chapter so that chapters can be written,
reviewed and diffed independently. The assembled PDF is built by
[`make report`](../makefile.md), which concatenates the files below in order.

| # | Chapter |
|---|---|
| — | [Frontmatter](00-frontmatter.md) — title, author, date |
| 1 | [Introduction](01-introduction.md) |
| 2 | [Dataset](02-dataset.md) |
| 3 | [Graph Construction](03-graph-construction.md) |
| 4 | [Algorithms](04-algorithms.md) |
| 5 | [Correctness Testing](05-correctness-testing.md) |
| 6 | [Complexity Analysis](06-complexity-analysis.md) |
| 7 | [Empirical Evaluation](07-empirical-evaluation.md) |
| 8 | [Visualization](08-visualization.md) |
| 9 | [Challenges and Lessons Learned](09-challenges-and-lessons-learned.md) |
| 10 | [Conclusion](10-conclusion.md) |
| 11 | [References](11-references.md) |
| A | [Code Inventory](12-appendix-a-code-inventory.md) |
| B | [Data Structures and the Public API](13-appendix-b-data-structures.md) |
| C | [Distance Formulas](14-appendix-c-distance-formulas.md) |
| D | [Validation against NetworkX](15-appendix-d-networkx-parity.md) |
| E | [A\* and Heuristic Consistency](16-appendix-e-astar-consistency.md) |
| F | [Reproducibility: Snapshots and Experiments](17-appendix-f-reproducibility.md) |
| G | [Glossary](18-appendix-g-glossary.md) |

The appendices are ordered to match the chapters that cite them, not by when
they were written: A accounts for the code the chapters argue about, B and C
back §3 and §4.3, D and E hold the full results §5 summarises, F describes the
machinery every figure depends on, and G is the glossary. Five of them — B, C, D, E and G — began life as documents under
`docs/` and were moved here once it was clear they served one part of the
report rather than the repository as a whole.

## Two files that are not chapters

- **`00-frontmatter.md`** holds the YAML block pandoc turns into the title
  page. It carries no prose, which is why it looks near-empty on GitHub. Its
  `#` heading is marked `{.unnumbered .unlisted}` so that it stays out of the
  PDF's table of contents, where it would only repeat the title page.
- **`newpage.md`** holds a bare `\newpage`. The Makefile interleaves it between
  chapters so each one starts on a fresh page in the PDF. It is a file rather
  than a directive inside the chapters because GitHub renders each chapter file
  on its own — a `\newpage` written inline would show up as literal text in
  every chapter, and this way it shows up in none of them.

## Heading levels

**A chapter's own title is `#`, its sections are `##`.** Pandoc concatenates
the chapter files before parsing, so the levels have to agree across files or
the table of contents indents one chapter under another. `00-frontmatter.md`
also uses `#`, but marks it `{.unnumbered .unlisted}` so it stays out of the
contents page. `--toc-depth=3` therefore lists chapters and their sections,
with one level spare.

## Slides live in the chapters

The reveal.js deck has no content of its own. Every content slide is a block
inside the chapter it summarises:

```markdown
<div class="deck-slide" id="cleaning">

### Cleaning: what got dropped, and why

...

</div>
```

Exactly one of two lua filters runs on every build. `drop-slides.lua` deletes
these blocks, so the PDF carries only prose; `deck-slides.lua` keeps only
these blocks, and writes each one out as its own file under `build/deck/`.
There is one source, so the report and the deck cannot say different things —
which is precisely what went wrong with the Google Slides deck this replaces.

Three rules, each enforced by [`tests/deck/`](../../tests/deck/):

1. **The blank lines are load-bearing.** CommonMark ends an HTML block at a
   blank line, which is what lets GitHub render the inner markdown and hide the
   wrapper. Without them pandoc reads the whole thing as one raw HTML block,
   `deck-slides.lua` never sees a `Div`, and **the slide vanishes from the deck
   with no error.**
2. **Every slide needs an `id`.** It is the slide's name in
   [`docs/deck/manifest.txt`](../deck/manifest.txt), which sets presentation
   order.
3. **The first `###` inside the block is the slide title**, promoted to `##` on
   the way out because reveal starts a new `<section>` at `--slide-level=2`.

The wrapper is HTML rather than pandoc's `::: deck-slide` because GitHub has no
fenced-div support and would render the colons literally. The HTML form parses
to the same pandoc AST node, and GitHub drops the unknown class.

## Adding a chapter

Add the file here, then add it to `REPORT_CHAPTERS` in the
[`Makefile`](../../Makefile). The order in that variable is the order of the
PDF; the filename prefixes are for humans reading the directory listing. The
contents page is generated from the headings, so it picks up the new chapter
with no further edit.
