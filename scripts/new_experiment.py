"""Scaffold an experiment directory pinned to a snapshot.

An experiment is a directory holding `experiment.toml`, one or more notebooks,
and eventually `results.json`. This writes the first two, with the snapshot
recorded as a path *relative to the experiment*, so the whole thing keeps
working from a source checkout, a fresh clone, or a Colab session -- wherever
the repository happens to have been put.

The generated notebook is a working starting point rather than a placeholder:
it opens the experiment, verifies the data, finds a route, and records the
result.

This half of the experiment machinery knows the repository's layout, which is
why it lives in `scripts/` and is not shipped in the wheel.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

from flight_planner.experiments import Snapshot  # noqa: E402

DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "data" / "snapshots"
DEFAULT_EXPERIMENT_ROOT = REPO_ROOT / "experiments"
DEFAULT_NOTEBOOK = "explore.ipynb"


def latest_snapshot(root: Path) -> Path:
    """Return the most recently frozen snapshot under a directory.

    Ordered by the manifest's `created` timestamp rather than by directory
    name: an id is `<date>-<content hash>`, so two snapshots frozen on the
    same day sort arbitrarily by name.

    Args:
        root: Directory holding snapshot directories.

    Returns:
        Path to the newest snapshot.

    Raises:
        FileNotFoundError: If there are no snapshots to choose from.
    """
    candidates = []
    for directory in sorted(root.iterdir()) if root.is_dir() else []:
        if not (directory / "manifest.json").is_file():
            continue
        snapshot = Snapshot.open(directory, verify=False)
        candidates.append((snapshot.created or "", directory))
    if not candidates:
        raise FileNotFoundError(
            f"no snapshots under {root}; run `make snapshot` before creating "
            f"an experiment, or pass --snapshot"
        )
    return max(candidates)[1]


def resolve_snapshot(reference: Optional[str], root: Path) -> Path:
    """Work out which snapshot an experiment should pin.

    Args:
        reference: A snapshot id, a path, or `None` for the newest one.
        root: Directory holding snapshot directories.

    Returns:
        Path to the snapshot.

    Raises:
        FileNotFoundError: If the named snapshot does not exist, or there are
            none to fall back on.
    """
    if reference is None:
        return latest_snapshot(root)

    for candidate in (Path(reference), root / reference):
        if (candidate / "manifest.json").is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"no snapshot {reference!r} in {root} or on disk")


def snapshot_reference(snapshot_dir: Path, directory: Path) -> str:
    """Return how an experiment should name its snapshot.

    Relative when the two live in the same tree, which is the normal case and
    what lets the repository be cloned anywhere. Absolute when they do not,
    because a relative path that climbs out to the filesystem root is not a
    portable reference -- it is a long way of writing an absolute one.

    Args:
        snapshot_dir: Resolved path to the snapshot.
        directory: Resolved path to the experiment directory.

    Returns:
        The path to record in `experiment.toml`.
    """
    try:
        common = Path(os.path.commonpath([snapshot_dir, directory]))
    except ValueError:  # Different drives on Windows.
        return str(snapshot_dir)
    if common == Path(common.anchor):
        return str(snapshot_dir)
    return os.path.relpath(snapshot_dir, directory)


def config_text(
    slug: str, description: str, notebook: str, snapshot: str, snapshot_id: str
) -> str:
    """Render an `experiment.toml`.

    Args:
        slug: The experiment's short name.
        description: What the experiment is trying to find out.
        notebook: Notebook filename.
        snapshot: Path to the snapshot, relative to the experiment directory.
        snapshot_id: The snapshot's id, for the explanatory comment.

    Returns:
        The file's contents.
    """
    return f'''# {slug}
#
# The snapshot path is relative to this file and resolved against its own
# location, so the experiment travels with the repository. Changing it points
# the experiment at different data -- record a new result if you do.
slug = {json.dumps(slug)}
description = {json.dumps(description)}
notebooks = [{json.dumps(notebook)}]
snapshot = {json.dumps(snapshot)}  # {snapshot_id}

# Whatever the notebook needs that is not the data itself. Recorded into
# results.json alongside the results, so a run states its own inputs.
[parameters]
origin = "SFO"
destination = "BOS"
'''


def notebook_json(slug: str, description: str) -> str:
    """Render a starter notebook that runs end to end as written.

    Args:
        slug: The experiment's short name.
        description: What the experiment is trying to find out.

    Returns:
        The `.ipynb` file's contents.
    """
    def cell(kind: str, source: List[str]) -> Dict[str, Any]:
        body = [line + "\n" for line in source[:-1]] + [source[-1]]
        if kind == "markdown":
            return {"cell_type": "markdown", "metadata": {}, "source": body}
        return {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": body,
        }

    cells = [
        cell("markdown", [
            f"# {slug}",
            "",
            description or "_Describe what this experiment is trying to find out._",
            "",
            "The data is pinned by `experiment.toml` and verified on load: if a",
            "byte of the snapshot changes, this notebook raises instead of",
            "quietly producing a different answer.",
        ]),
        cell("markdown", ["## Setup", "", "Only the first cell differs between Colab and a local checkout."]),
        cell("code", [
            "# In Colab, clone the repository and install the package first:",
            "#   !git clone https://github.com/<owner>/traiectoria-optima.git",
            "#   %pip install -q ./traiectoria-optima",
            "# Then open this notebook from the clone.",
            "try:",
            "    import flight_planner  # noqa: F401",
            "except ModuleNotFoundError as error:",
            "    raise SystemExit(\"install the package first -- see the comment above\") from error",
        ]),
        cell("code", [
            "from pathlib import Path",
            "",
            "from flight_planner.experiments import Experiment",
            "",
            "# The notebook lives in the experiment directory, so the experiment is",
            "# right here. Nothing resolves against a repository root.",
            "experiment = Experiment.open(Path.cwd())",
            "experiment, experiment.parameters",
        ]),
        cell("markdown", ["## The data", "", "Opening the snapshot re-hashes every file against the manifest."]),
        cell("code", [
            "snapshot = experiment.snapshot",
            "print(snapshot.snapshot_id, snapshot.criteria)",
            "",
            "catalog = experiment.catalog()",
            "catalog",
        ]),
        cell("markdown", [
            "Narrow the catalog if the experiment works on part of the network.",
            "Every narrowing records what it cost, and the chain goes into the",
            "results:",
            "",
            "```python",
            "catalog = catalog.airline('UA').airport_type('large')",
            "catalog.summary()",
            "```",
        ]),
        cell("markdown", ["## The question"]),
        cell("code", [
            "planner = catalog.planner()",
            "",
            "origin = experiment.parameters['origin']",
            "destination = experiment.parameters['destination']",
            "distance_km, legs = planner.find_shortest_route(origin, destination)",
            "",
            "print(f'{distance_km:,.1f} km in {len(legs)} leg(s)')",
            "for leg in legs:",
            "    print(f'  {leg.flight_number}  {leg.origin.city} -> {leg.destination.city}')",
        ]),
        cell("markdown", ["## The answer", "", "Recorded next to the data that produced it."]),
        cell("code", [
            "experiment.record(",
            "    {",
            "        'shortest_km': distance_km,",
            "        'legs': len(legs),",
            "        'flights': [leg.flight_number for leg in legs],",
            "    },",
            "    catalog=catalog,",
            ")",
        ]),
    ]

    payload = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(payload, indent=1) + "\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse the slug and options from the command line.

    Args:
        argv: Argument list, or `None` to read `sys.argv`.

    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slug", help="Directory name and identifier for the experiment.")
    parser.add_argument(
        "--snapshot",
        help="Snapshot id or path to pin. Defaults to the most recent snapshot.",
    )
    parser.add_argument("--description", default="", help="What the experiment asks.")
    parser.add_argument("--notebook", default=DEFAULT_NOTEBOOK, help="Notebook filename.")
    parser.add_argument("--root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    parser.add_argument("--snapshot-root", type=Path, default=DEFAULT_SNAPSHOT_ROOT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing experiment.toml. Never touches notebooks.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Create an experiment directory.

    Args:
        argv: Argument list, or `None` to read `sys.argv`.

    Returns:
        Process exit status: 0 on success, 1 if the experiment already exists.
    """
    args = parse_args(argv)

    directory = args.root / args.slug
    if (directory / "experiment.toml").exists() and not args.force:
        print(
            f"{directory}/experiment.toml already exists; pass --force to "
            f"overwrite it",
            file=sys.stderr,
        )
        return 1

    snapshot_dir = resolve_snapshot(args.snapshot, args.snapshot_root)
    snapshot = Snapshot.open(snapshot_dir, verify=False)

    directory.mkdir(parents=True, exist_ok=True)
    relative = snapshot_reference(snapshot_dir, directory.resolve())
    (directory / "experiment.toml").write_text(
        config_text(
            args.slug, args.description, args.notebook, relative, snapshot.snapshot_id
        )
    )

    # A notebook is the experimenter's work and is never overwritten, not
    # even by --force: that flag is about the generated config.
    notebook_path = directory / args.notebook
    if not notebook_path.exists():
        notebook_path.write_text(notebook_json(args.slug, args.description))

    print(f"experiment: {directory}")
    print(f"  snapshot: {relative} ({snapshot.snapshot_id})")
    print(f"  notebook: {notebook_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
