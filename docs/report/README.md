# Final Report — chapters

The final report is split one file per chapter so that chapters can be written,
reviewed and diffed independently. The assembled PDF is built by
[`make report`](../makefile.md), which concatenates the files below in order.

| # | Chapter |
|---|---|
| — | [Frontmatter](00-frontmatter.md) — title, authors, date |
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
| — | [Appendix](12-appendix.md) |

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

## Adding a chapter

Add the file here, then add it to `REPORT_CHAPTERS` in the
[`Makefile`](../../Makefile). The order in that variable is the order of the
PDF; the filename prefixes are for humans reading the directory listing. The
contents page is generated from the headings, so it picks up the new chapter
with no further edit.
