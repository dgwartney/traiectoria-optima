"""Example: an experiment written as a plain script instead of a notebook.

`notebooks` in `experiment.toml` is a list of filenames. Nothing checks the
extension, so an experiment can just as well be a `.py` file living in the
experiment directory next to its config and its results.

One thing changes when it is. A notebook can call
`Experiment.open(Path.cwd())`, because a notebook's working directory is the
directory it sits in. A script's working directory is wherever the caller
happened to be standing, so a script must locate itself:

    Experiment.open(Path(__file__).resolve().parent)

This demo builds a throwaway experiment whose notebook is a script, runs that
script as a separate process from an unrelated working directory to prove the
self-location works, and then shows what it recorded. It finishes by running
the same script with the `Path.cwd()` mistake, so the failure is visible rather
than theoretical.

Run from anywhere:
    uv run python src/demos/script_experiment_example.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from flight_planner.experiments import Experiment

REPOSITORY = Path(__file__).resolve().parents[2]
SNAPSHOT = REPOSITORY / "data" / "snapshots" / "2026-09-11-bb90a8"

CONFIG = """\
slug = "script-experiment"
description = "Does the shortest route change when the network is narrowed to one carrier?"
notebooks = ["run.py"]
snapshot = "{snapshot}"

[parameters]
airline = "UA"
pairs = [["SFO", "BOS"], ["BOI", "CHS"]]
"""

# The experiment itself. Written to `run.py` inside the experiment directory,
# which is what `notebooks` names -- the same role `explore.ipynb` plays in a
# notebook-based experiment.
SCRIPT = '''\
"""Compare the whole network against one carrier's, and record the result."""

from pathlib import Path

from flight_planner.experiments import Experiment


def main() -> int:
    """Run the experiment and record what it found.

    Returns:
        Process exit status.
    """
    # A script cannot use Path.cwd(): it is wherever the caller stood. The
    # experiment is the directory this file lives in.
    experiment = Experiment.open(Path(__file__).resolve().parent)
    parameters = experiment.parameters

    whole = experiment.catalog()
    narrowed = whole.airline(parameters["airline"])

    whole_planner, narrowed_planner = whole.planner(), narrowed.planner()

    rows = []
    for origin, destination in parameters["pairs"]:
        whole_km, whole_legs = whole_planner.find_shortest_route(origin, destination)
        narrowed_km, narrowed_legs = narrowed_planner.find_shortest_route(
            origin, destination
        )
        rows.append(
            {
                "pair": f"{origin}-{destination}",
                "whole_km": whole_km,
                "whole_legs": len(whole_legs),
                "narrowed_km": narrowed_km,
                "narrowed_legs": len(narrowed_legs),
            }
        )
        print(
            f"  {origin}-{destination}: {whole_km:,.1f} km whole network, "
            f"{narrowed_km:,.1f} km narrowed"
        )

    # record() opens the snapshot -- verifying every checksum -- before writing.
    experiment.record({"pairs": rows}, catalog=narrowed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# The same script with the mistake in it, to show what going wrong looks like.
BROKEN_SCRIPT = SCRIPT.replace(
    "Experiment.open(Path(__file__).resolve().parent)", "Experiment.open(Path.cwd())"
)


def build(directory: Path, script: str = SCRIPT) -> Path:
    """Write a script-based experiment into a directory.

    Args:
        directory: Directory to write `experiment.toml` and the script to.
        script: Source of the script named by `notebooks`.

    Returns:
        Path to the written script.
    """
    (directory / "experiment.toml").write_text(CONFIG.format(snapshot=SNAPSHOT))
    script_path = directory / "run.py"
    script_path.write_text(script)
    return script_path


def describe(directory: Path) -> None:
    """Report what the experiment declares, before anything has run it.

    Args:
        directory: The experiment directory.
    """
    experiment = Experiment.open(directory)
    print(f"--- {experiment.slug} ---")
    print(f"Question:  {experiment.description}")

    # Nothing about `notebooks` requires a notebook: this one names a script,
    # and Experiment neither checks the extension nor requires the file to
    # exist yet.
    print(f"Code:      {', '.join(experiment.notebooks)}")
    print(f"Snapshot:  {experiment.snapshot_path.name}")


def run(script_path: Path, cwd: Path) -> subprocess.CompletedProcess:
    """Run a script-based experiment as its own process.

    Args:
        script_path: The script to run.
        cwd: Working directory to run it from -- deliberately not the
            experiment's own directory.

    Returns:
        The completed process, with output captured.
    """
    return subprocess.run(
        [sys.executable, str(script_path)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> None:
    """Build, run and report a script-based experiment."""
    with tempfile.TemporaryDirectory() as workspace:
        workspace = Path(workspace)
        experiment_dir = workspace / "script-experiment"
        experiment_dir.mkdir()

        script_path = build(experiment_dir)
        describe(experiment_dir)

        # Run it from the temporary root rather than from the experiment
        # directory, so nothing but `__file__` could have located the config.
        print(f"\nRunning {script_path.name} with cwd={workspace.name}/ ...")
        completed = run(script_path, cwd=workspace)
        print(completed.stdout.rstrip())

        recorded = json.loads((experiment_dir / "results.json").read_text())
        print("\nRecorded, with the data it came from:")
        print(f"  snapshot:   {recorded['snapshot']['id']}")
        print(f"  parameters: {recorded['parameters']}")
        print(f"  narrowing:  routes {recorded['catalog']['routes']}")

        # The same experiment with Path.cwd() instead of __file__, run from a
        # directory that holds no experiment.toml.
        broken_dir = workspace / "broken"
        broken_dir.mkdir()
        broken_path = build(broken_dir, BROKEN_SCRIPT)

        print("\nThe same script using Path.cwd() instead, run from elsewhere:")
        failed = run(broken_path, cwd=workspace)
        print(f"  exit status {failed.returncode}")
        print(f"  {failed.stderr.strip().splitlines()[-1]}")
        print("\nWhich is why a script locates itself and a notebook need not.")


if __name__ == "__main__":
    main()
