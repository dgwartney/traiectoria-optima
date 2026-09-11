"""An immutable, checksummed copy of the airport and route data.

An experiment's results are only meaningful next to the data that produced
them, and `data/processed/` is regenerated whenever the pipeline runs. A
snapshot is that data frozen: the CSV files plus a manifest recording a
SHA-256 for each, so a later run can prove it read the same bytes.

The manifest is the contract. `Snapshot` knows its format and nothing about
where a repository keeps its snapshots -- it is handed a directory. That is
what lets the same code work from a source checkout, an installed wheel, or a
clone in a Colab session.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Union

from ..flights.planner import FlightPlanner
from ..loaders.csv_loader import AirportLoader, RouteLoader, load_flight_planner
from .catalog import Catalog

PathLike = Union[str, Path]

MANIFEST_FILENAME = "manifest.json"

#: Read in blocks rather than whole: a global snapshot's routes file is
#: several megabytes, and verification happens on every open.
_HASH_BLOCK_BYTES = 1 << 20


class SnapshotIntegrityError(Exception):
    """Raised when a snapshot's contents do not match its manifest.

    Either the manifest cannot be understood, or a file it vouches for is
    missing or has changed since it was frozen.
    """


class Snapshot:
    """Frozen data, verified against its manifest.

    Attributes:
        directory: Directory the snapshot lives in.
    """

    def __init__(self, directory: Path, manifest: Mapping[str, Any]) -> None:
        """Bind a snapshot to its directory and already-parsed manifest.

        Prefer `Snapshot.open`, which parses and verifies. This constructor
        assumes both have already been done.

        Args:
            directory: Directory holding the snapshot's files.
            manifest: Parsed manifest contents.
        """
        self.directory = directory
        self._manifest = manifest

    @classmethod
    def open(cls, directory: PathLike, verify: bool = True) -> "Snapshot":
        """Open a snapshot and check its contents against the manifest.

        Args:
            directory: Directory holding `manifest.json` and the data files.
            verify: Whether to re-hash every file the manifest lists. Leave
                this on unless the cost is known to matter; skipping it means
                nothing detects a changed file.

        Returns:
            The opened `Snapshot`.

        Raises:
            FileNotFoundError: If the directory or its manifest is absent.
            SnapshotIntegrityError: If the manifest cannot be parsed, or a
                file it lists is missing or no longer matches its checksum.
        """
        directory = Path(directory)
        manifest_path = directory / MANIFEST_FILENAME
        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"{directory} is not a snapshot: no {MANIFEST_FILENAME}"
            )

        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            raise SnapshotIntegrityError(
                f"{manifest_path} is not valid JSON: {error}"
            ) from error

        if not isinstance(manifest.get("files"), dict):
            raise SnapshotIntegrityError(
                f"{manifest_path} has no 'files' section to verify against"
            )

        snapshot = cls(directory, manifest)
        if verify:
            snapshot.verify()
        return snapshot

    @property
    def snapshot_id(self) -> str:
        """Return the snapshot's identifier.

        Returns:
            The id recorded in the manifest, normally `<date>-<short hash>`.
        """
        return str(self._manifest.get("snapshot_id", self.directory.name))

    @property
    def criteria(self) -> Mapping[str, Any]:
        """Return the narrowing that produced this slice.

        Returns:
            Mapping of criterion to value, empty for a full snapshot.
        """
        return dict(self._manifest.get("criteria") or {})

    @property
    def created(self) -> Optional[str]:
        """Return when the snapshot was frozen.

        Returns:
            ISO-8601 timestamp, or `None` if it was not recorded.
        """
        return self._manifest.get("created")

    @property
    def source_commit(self) -> Optional[str]:
        """Return the commit the snapshot was generated from.

        Returns:
            The commit SHA, or `None` if it was not recorded.
        """
        return self._manifest.get("source_commit")

    @property
    def filenames(self) -> tuple:
        """Return the files the manifest vouches for.

        Returns:
            Tuple of filenames, in manifest order.
        """
        return tuple(self._manifest["files"])

    def path(self, filename: str) -> Path:
        """Return the path to one of the snapshot's files.

        Only files the manifest lists can be reached, so nothing unverified
        is ever handed out.

        Args:
            filename: Name of the file within the snapshot.

        Returns:
            Absolute path to the file.

        Raises:
            KeyError: If the manifest does not list the file.
        """
        if filename not in self._manifest["files"]:
            raise KeyError(
                f"{filename!r} is not in {self.snapshot_id}; "
                f"it holds {', '.join(self.filenames)}"
            )
        return self.directory / filename

    def verify(self) -> None:
        """Re-hash every file the manifest lists and compare.

        Raises:
            SnapshotIntegrityError: On the first file that is missing or whose
                contents no longer match the recorded checksum.
        """
        for filename, recorded in self._manifest["files"].items():
            path = self.directory / filename
            if not path.is_file():
                raise SnapshotIntegrityError(
                    f"{self.snapshot_id}: {filename} is listed in the manifest "
                    f"but missing from {self.directory}"
                )
            actual = self._digest(path)
            expected = recorded.get("sha256")
            if actual != expected:
                raise SnapshotIntegrityError(
                    f"{self.snapshot_id}: {filename} has changed since it was "
                    f"frozen (expected sha256 {expected}, found {actual})"
                )

    def load_planner(self) -> FlightPlanner:
        """Build a `FlightPlanner` from this snapshot's data.

        Returns:
            A planner holding every airport and route in the snapshot.
        """
        return load_flight_planner(self.path("airports.csv"), self.path("routes.csv"))

    def catalog(self) -> Catalog:
        """Open this snapshot's data as a narrowable catalog.

        The whole snapshot is the starting scope; narrow it before calling
        `Catalog.planner()` to work with a slice.

        Returns:
            A `Catalog` over every airport and route in the snapshot.
        """
        airports = AirportLoader(self.path("airports.csv")).load_by_iata()
        routes = RouteLoader(airports, self.path("routes.csv")).load()
        return Catalog(airports.values(), routes)

    @staticmethod
    def _digest(path: Path) -> str:
        """Return the SHA-256 of a file.

        Args:
            path: File to hash.

        Returns:
            Hex digest of the file's contents.
        """
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(_HASH_BLOCK_BYTES), b""):
                digest.update(block)
        return digest.hexdigest()

    def __repr__(self) -> str:
        """Return a debugging representation naming the snapshot and its files.

        Returns:
            String of the form `Snapshot('<id>', files=[...])`.
        """
        return f"Snapshot({self.snapshot_id!r}, files={list(self.filenames)})"
