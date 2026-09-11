# Python Documentation Standard

This document defines how code should be documented in this project.

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

## Summary

| Concern | Tool |
|---|---|
| Docstring format | Google style |
| Type info | Type hints (not repeated in docstrings) |
| Linting | `ruff` with `select = ["D"]`, `convention = "google"` |
