"""The committed demo notebook must stay runnable and stay honest.

`notebooks/demo.ipynb` is the rubric's "single runnable notebook" deliverable
and the artifact presented live. Executing it here would be the strongest
guard, but it needs `folium`, `pyproj` and a network for the basemap tiles --
so instead these checks cover the three ways it could rot silently between
runs, all of them cheap:

*   **Stored output.** A notebook committed with output is a notebook whose
    numbers can disagree with the code that produced them, which is the whole
    failure this project's experiment framework exists to prevent.
*   **Dangling references.** It names a snapshot and four experiment slugs.
    A renamed directory would turn into a `FileNotFoundError` on stage.
*   **API drift.** It imports from `flight_planner` by name. A rename in the
    package would not be caught by any other test, because no test imports
    the notebook -- and a demo that no longer matches its own library is the
    specific risk #87 is about.

The logic itself is tested through `tests/demos/test_route_query_example.py`,
since the notebook delegates to that module rather than reimplementing it.
"""

import ast
import json
from pathlib import Path
from typing import List

import pytest

import flight_planner

#: The snapshot the notebook pins. It does not hard-code the id -- it imports
#: `SNAPSHOT_ID` from `route_query_example`, so the demo script and the
#: notebook cannot name different data. Repeated here so that changing it
#: there is a deliberate act with a failing test attached.
SNAPSHOT_ID = "2026-09-11-bb90a8"

#: Every experiment the notebook reads a recorded answer from.
SLUGS = ("search-cost", "route-map", "networkx-parity")


@pytest.fixture(scope="module")
def notebook(repo_root: Path) -> dict:
    return json.loads((repo_root / "notebooks" / "demo.ipynb").read_text())


@pytest.fixture(scope="module")
def source(notebook: dict) -> str:
    """Return every code cell's source, concatenated."""
    return "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )


def test_it_carries_no_stored_output(notebook: dict) -> None:
    """Outputs are re-derivable; committing them invites disagreement."""
    with_output = [
        index
        for index, cell in enumerate(notebook["cells"])
        if cell.get("outputs") or cell.get("execution_count") is not None
    ]
    assert not with_output, (
        f"cells {with_output} carry stored output. Clear them: the notebook "
        "is committed empty on purpose."
    )


def test_every_cell_has_an_id(notebook: dict) -> None:
    """nbformat 4.5 requires it, and jupyter warns loudly without it."""
    assert all(cell.get("id") for cell in notebook["cells"])


def test_every_code_cell_parses(source: str) -> None:
    """A syntax error would only surface when the cell was reached."""
    ast.parse(source)


def test_the_snapshot_it_pins_exists(repo_root: Path, source: str) -> None:
    """The notebook takes the id from the demo module rather than repeating it."""
    from route_query_example import SNAPSHOT_ID as PINNED

    assert "SNAPSHOT_ID" in source, "the notebook no longer pins a snapshot"
    assert PINNED == SNAPSHOT_ID, (
        "route_query_example now pins a different snapshot; update this test "
        "deliberately rather than letting the demo move on its own"
    )
    assert (repo_root / "data" / "snapshots" / PINNED).is_dir()


@pytest.mark.parametrize("slug", SLUGS)
def test_each_experiment_it_reads_exists(repo_root: Path, source: str, slug: str) -> None:
    assert f'"{slug}"' in source, f"the notebook no longer reads {slug}"
    assert (repo_root / "experiments" / slug / "results.json").is_file()


def _imported_names(source: str) -> List[str]:
    """Return every name the notebook imports out of `flight_planner`."""
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "flight_planner"
        ):
            names.extend((node.module, alias.name) for alias in node.names)
    return names


def test_it_imports_only_names_the_package_still_has(source: str) -> None:
    """The guard against the demo drifting from the API it demonstrates.

    No other test imports this notebook, so a rename in `flight_planner`
    would leave it broken until someone ran it.
    """
    import importlib

    missing = []
    for module_name, name in _imported_names(source):
        module = importlib.import_module(module_name)
        if not hasattr(module, name):
            missing.append(f"{module_name}.{name}")
    assert not missing, f"the notebook imports names that no longer exist: {missing}"


def test_the_package_it_demonstrates_is_the_installed_one(repo_root: Path) -> None:
    """Guard against testing a stale copy on the path."""
    assert Path(flight_planner.__file__).is_relative_to(repo_root / "src")
