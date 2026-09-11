# Python Documentation Standard

This document defines how code should be documented in this project and how
that documentation is turned into a browsable site.

## Docstring style: Google

All modules, classes, and functions/methods should have a
[Google-style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
docstring. Google style was chosen over NumPy style and reST because it stays
readable as plain text in the terminal/editor while still being fully
machine-parseable, and it pairs cleanly with the type hints already used
throughout `src/`.

Rules:

- Every public module, class, and function/method gets a docstring.
- Private helpers (prefixed with `_`) only need a docstring if their behavior
  isn't obvious from the name and signature.
- Rely on type hints for types; don't repeat types in the docstring body.
- Wrap prose at a reasonable width (~88 chars, matching `ruff`'s line length).

### Function/method docstring

```python
def add_edge(self, from_vert: str, to_vert: str, weight: int = 0) -> None:
    """Add a weighted, directed edge between two vertices.

    Args:
        from_vert: Key of the source vertex.
        to_vert: Key of the destination vertex.
        weight: Edge weight, defaults to 0.

    Raises:
        KeyError: If either vertex is not already in the graph.
    """
```

### Class docstring

```python
class Graph:
    """An adjacency-list graph of Vertex objects.

    Attributes:
        vert_list: Mapping of vertex key to Vertex instance.
        num_vertices: Number of vertices currently in the graph.
    """
```

### Module docstring

Place at the top of the file, before imports:

```python
"""Adjacency-list graph implementation used by the routing examples."""
```

### Sections available in Google style

Use only the sections that apply — don't pad a docstring with empty
sections:

- `Args:` — parameters
- `Returns:` — return value
- `Yields:` — for generators
- `Raises:` — exceptions the caller should expect
- `Example:` / `Examples:` — short usage snippet, useful for non-obvious APIs

## Enforcement: ruff

Docstring presence and formatting are linted rather than left to convention.
`pyproject.toml` enables the `D` (pydocstyle) rule set, scoped to docstrings
only so it doesn't also surface unrelated pre-existing lint debt (line
length, unused imports, etc.):

```toml
[tool.ruff.lint]
select = ["D"]

[tool.ruff.lint.pydocstyle]
convention = "google"
```

Run `uv run ruff check` to see docstring violations.

## Generating documentation: MkDocs + mkdocstrings

This project uses [MkDocs](https://www.mkdocs.org/) with the
[mkdocstrings](https://mkdocstrings.github.io/) plugin, which reads
docstrings and type hints directly via introspection — no duplicate `.rst`
stub files to maintain.

MkDocs was chosen over Sphinx because it needs almost no boilerplate for a
flat `src/` layout with no `__init__.py` packages, and its Markdown-based
pages match the rest of `docs/`.

### What's already set up

- `mkdocs>=1.6`, `mkdocs-material>=9.5`, and `mkdocstrings[python]>=0.26` are
  in the `dev` dependency group in `pyproject.toml`.
- `mkdocs.yml` at the repo root configures the Material theme, the
  `mkdocstrings` Python handler (pointed at `src`, `src/data`,
  `src/models/flight`, `src/exercises`), and the site nav.
- `docs/index.md` is the site homepage.
- `docs/reference.md` holds the generated API reference, one `:::` directive
  per documented module:

  ```markdown
  ::: aircraft
  ::: atomosphere
  ::: simulator
  ::: wind
  ::: payload_range
  ::: flight_data
  ```

  `src/data/data_format.py` and `src/exercises/graphs/adjacency_list.py` are
  intentionally left out of the reference — both currently fail to import
  (a syntax error and undefined names, respectively). Add them once fixed.

### Building

```bash
uv run mkdocs serve   # live preview at http://127.0.0.1:8000
uv run mkdocs build   # writes static site to site/ (gitignored)
```

### Adding a new module to the reference

1. Write the module with Google-style docstrings (see above).
2. Add its directory to `plugins.mkdocstrings.handlers.python.paths` in
   `mkdocs.yml`, if it isn't already covered.
3. Add a `::: module_name` line to `docs/reference.md`.

## Summary

| Concern | Tool |
|---|---|
| Docstring format | Google style |
| Type info | Type hints (not repeated in docstrings) |
| Linting | `ruff` with `select = ["D"]`, `convention = "google"` |
| Doc generation | MkDocs + mkdocstrings (`mkdocs.yml`, `docs/reference.md`) |
