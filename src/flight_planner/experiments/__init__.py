"""Reproducible experiments: pinned data, and the results it produced.

The half of the experiment machinery that *reads*. A `Snapshot` is a directory
of frozen CSV files plus a manifest of checksums; opening one verifies that
the bytes are the bytes the experiment ran against. A `Catalog` is the scope an
experiment works in: it looks airports and routes up, narrows them, records
what each narrowing did, and materializes what is left as a `FlightPlanner`.
An `Experiment` binds a directory of notebooks to one snapshot and records what
the run produced.

Everything here takes a directory from its caller and holds no knowledge of
where a repository keeps its data, so it behaves the same from a source
checkout, an installed wheel, or a clone in a Colab session. Creating and
slicing snapshots is the repository's job and lives in `scripts/`.
"""

from .catalog import Catalog, Narrowing
from .experiment import Experiment
from .snapshot import Snapshot, SnapshotIntegrityError

__all__ = [
    "Catalog",
    "Experiment",
    "Narrowing",
    "Snapshot",
    "SnapshotIntegrityError",
]
