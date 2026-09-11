"""An experiment: pinned data, the code that reads it, and what it produced.

An experiment is a directory. `experiment.toml` declares which snapshot it
runs against and which notebooks make it up; `results.json` records what came
out, next to the identity of the data that went in. Both live in git, so a
result can always be traced to the bytes that produced it.

The snapshot is named by a path *relative to the toml file*, resolved against
that file's own location -- never against the working directory and never by
walking up from `__file__`. That is what lets the same experiment run from a
source checkout, from a clone in a Colab session, or from any directory at
all.

Creating experiments belongs to the repository and lives in `scripts/`; this
module only reads them and records their output.
"""

from __future__ import annotations

import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple, Union

from .catalog import Catalog
from .snapshot import Snapshot

PathLike = Union[str, Path]

CONFIG_FILENAME = "experiment.toml"
RESULTS_FILENAME = "results.json"


class Experiment:
    """A directory holding an experiment's configuration and results.

    Attributes:
        directory: Directory the experiment lives in.
    """

    def __init__(self, directory: Path, config: Mapping[str, Any]) -> None:
        """Bind an experiment to its directory and already-parsed config.

        Prefer `Experiment.open`, which reads and validates the file.

        Args:
            directory: Directory holding `experiment.toml`.
            config: Parsed contents of that file.
        """
        self.directory = directory
        self._config = config
        self._snapshot: Optional[Snapshot] = None

    @classmethod
    def open(cls, directory: PathLike) -> "Experiment":
        """Read an experiment's configuration.

        The snapshot is *not* opened here. Verification re-hashes every file,
        which is worth doing exactly once and only when the data is actually
        wanted, so it waits until `snapshot` is first touched.

        Args:
            directory: Directory holding `experiment.toml`.

        Returns:
            The opened `Experiment`.

        Raises:
            FileNotFoundError: If the directory or its `experiment.toml` is
                absent.
            ValueError: If the file is not valid TOML, or does not name a
                snapshot.
        """
        directory = Path(directory)
        config_path = directory / CONFIG_FILENAME
        if not config_path.is_file():
            raise FileNotFoundError(
                f"{directory} is not an experiment: no {CONFIG_FILENAME}"
            )

        try:
            config = tomllib.loads(config_path.read_text())
        except tomllib.TOMLDecodeError as error:
            raise ValueError(f"{config_path} is not valid TOML: {error}") from error

        if not config.get("snapshot"):
            raise ValueError(
                f"{config_path} does not name a snapshot. An experiment is "
                f"pinned to its data: add snapshot = \"<relative path>\"."
            )

        return cls(directory, config)

    # ------------------------------------------------------------ what it is

    @property
    def slug(self) -> str:
        """Return the experiment's short name.

        Returns:
            The declared slug, or the directory name if none was declared.
        """
        return str(self._config.get("slug") or self.directory.name)

    @property
    def description(self) -> str:
        """Return what the experiment is trying to find out.

        Returns:
            The declared description, or `""`.
        """
        return str(self._config.get("description", ""))

    @property
    def notebooks(self) -> Tuple[str, ...]:
        """Return the notebooks making up the experiment.

        Returns:
            Tuple of filenames, in declaration order.
        """
        return tuple(self._config.get("notebooks") or ())

    @property
    def notebook_paths(self) -> Tuple[Path, ...]:
        """Return the notebooks as paths inside the experiment directory.

        Existence is not checked: a notebook can be declared before it is
        written.

        Returns:
            Tuple of `Path`, in declaration order.
        """
        return tuple(self.directory / name for name in self.notebooks)

    @property
    def parameters(self) -> Dict[str, Any]:
        """Return the experiment's declared inputs.

        Anything the notebook needs that is not the data itself -- an origin
        airport, a heuristic name, a cutoff. Recorded alongside the results so
        a run states its own inputs.

        Returns:
            Mapping of parameter name to value, empty if none were declared.
        """
        return dict(self._config.get("parameters") or {})

    # ---------------------------------------------------------- what it reads

    @property
    def snapshot_reference(self) -> str:
        """Return the snapshot path exactly as the config names it.

        Returns:
            The unresolved string, normally relative to the experiment.
        """
        return str(self._config["snapshot"])

    @property
    def snapshot_path(self) -> Path:
        """Return the resolved location of the experiment's snapshot.

        Relative paths resolve against the experiment directory, so the
        experiment moves with its repository and depends on no working
        directory.

        Returns:
            Absolute path to the snapshot directory.
        """
        reference = Path(self.snapshot_reference)
        if reference.is_absolute():
            return reference
        return (self.directory / reference).resolve()

    @property
    def snapshot(self) -> Snapshot:
        """Return the experiment's data, verified against its manifest.

        Opened and verified on first access, then reused.

        Returns:
            The `Snapshot` this experiment is pinned to.

        Raises:
            FileNotFoundError: If the snapshot is not where the config says,
                named together with the experiment that pointed there.
            SnapshotIntegrityError: If the data has changed since it was
                frozen.
        """
        if self._snapshot is None:
            try:
                self._snapshot = Snapshot.open(self.snapshot_path)
            except FileNotFoundError as error:
                raise FileNotFoundError(
                    f"experiment {self.slug!r} is pinned to "
                    f"{self.snapshot_reference!r}, which is not a snapshot: "
                    f"{error}"
                ) from error
        return self._snapshot

    def catalog(self) -> Catalog:
        """Open the experiment's data as a narrowable catalog.

        Returns:
            A `Catalog` over the whole snapshot.
        """
        return self.snapshot.catalog()

    # --------------------------------------------------------- what it found

    @property
    def results_path(self) -> Path:
        """Return where this experiment's results are written.

        Returns:
            Path to `results.json` inside the experiment directory.
        """
        return self.directory / RESULTS_FILENAME

    def record(
        self, results: Mapping[str, Any], catalog: Optional[Catalog] = None
    ) -> Path:
        """Write what the experiment found, next to what it ran against.

        Results alone are not reproducible, so the record carries the
        snapshot's identity, criteria and source commit, the declared
        parameters, and -- when a catalog is supplied -- the narrowing chain
        that derived the graph. Touching the snapshot means the data is
        verified before any result claims to come from it.

        A previous run is replaced: git holds the history, so the file holds
        only the current answer.

        Args:
            results: What the experiment found. Must be JSON-serializable.
            catalog: The catalog the graph was built from, if the experiment
                narrowed the data. Its `summary()` is embedded.

        Returns:
            Path to the written `results.json`.

        Raises:
            TypeError: If `results` contains something JSON cannot represent.
            SnapshotIntegrityError: If the data has changed since it was
                frozen.
        """
        snapshot = self.snapshot
        payload: Dict[str, Any] = {
            "experiment": self.slug,
            "recorded": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "snapshot": {
                "id": snapshot.snapshot_id,
                "reference": self.snapshot_reference,
                "criteria": dict(snapshot.criteria),
                "source_commit": snapshot.source_commit,
            },
            "parameters": self.parameters,
            "results": dict(results),
        }
        if catalog is not None:
            payload["catalog"] = dict(catalog.summary())

        # Serialize before opening the file, so an unserializable result
        # leaves the previous run intact rather than truncating it.
        text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
        self.results_path.write_text(text)
        return self.results_path

    def results(self) -> Optional[Mapping[str, Any]]:
        """Return the last recorded run.

        Returns:
            The parsed `results.json`, or `None` if the experiment has not
            been run yet.

        Raises:
            ValueError: If the file exists but is not valid JSON.
        """
        if not self.results_path.is_file():
            return None
        try:
            return json.loads(self.results_path.read_text())
        except json.JSONDecodeError as error:
            raise ValueError(
                f"{self.results_path} is not valid JSON: {error}"
            ) from error

    def __repr__(self) -> str:
        """Return a debugging representation naming the experiment and its data.

        Returns:
            String of the form `Experiment('<slug>', snapshot='<ref>')`.
        """
        return f"Experiment({self.slug!r}, snapshot={self.snapshot_reference!r})"
