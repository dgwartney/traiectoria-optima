import json

import pytest

import new_experiment
from flight_planner.experiments import Experiment


@pytest.fixture
def snapshots(tmp_path, make_snapshot):
    """Two snapshots, the second frozen later than the first."""
    root = tmp_path / "data" / "snapshots"
    make_snapshot(root / "2026-09-10-older", created="2026-09-10T00:00:00+00:00")
    make_snapshot(root / "2026-09-11-newer", created="2026-09-11T00:00:00+00:00")
    return root


@pytest.fixture
def args(snapshots, tmp_path):
    return ["--root", str(tmp_path / "experiments"), "--snapshot-root", str(snapshots)]


class TestScaffolding:
    def test_writes_the_config_and_the_notebook(self, args, tmp_path):
        new_experiment.main(["sfo-bos"] + args)

        directory = tmp_path / "experiments" / "sfo-bos"
        assert (directory / "experiment.toml").is_file()
        assert (directory / "explore.ipynb").is_file()

    def test_the_result_opens_as_an_experiment(self, args, tmp_path):
        new_experiment.main(["sfo-bos", "--description", "why"] + args)

        experiment = Experiment.open(tmp_path / "experiments" / "sfo-bos")
        assert experiment.slug == "sfo-bos"
        assert experiment.description == "why"
        assert experiment.notebooks == ("explore.ipynb",)
        assert experiment.snapshot.snapshot_id == "2026-09-11-newer"

    def test_the_snapshot_is_named_relatively(self, args, tmp_path):
        new_experiment.main(["sfo-bos"] + args)

        reference = Experiment.open(
            tmp_path / "experiments" / "sfo-bos"
        ).snapshot_reference
        assert not reference.startswith("/")
        assert reference.endswith("2026-09-11-newer")

    def test_parameters_are_scaffolded(self, args, tmp_path):
        new_experiment.main(["sfo-bos"] + args)

        assert Experiment.open(tmp_path / "experiments" / "sfo-bos").parameters == {
            "origin": "SFO",
            "destination": "BOS",
        }

    def test_the_notebook_is_valid(self, args, tmp_path):
        new_experiment.main(["sfo-bos"] + args)

        notebook = json.loads(
            (tmp_path / "experiments" / "sfo-bos" / "explore.ipynb").read_text()
        )
        assert notebook["nbformat"] == 4
        assert [cell["cell_type"] for cell in notebook["cells"]].count("code") >= 4

    def test_a_custom_notebook_name_is_honoured(self, args, tmp_path):
        new_experiment.main(["sfo-bos", "--notebook", "analysis.ipynb"] + args)

        directory = tmp_path / "experiments" / "sfo-bos"
        assert (directory / "analysis.ipynb").is_file()
        assert Experiment.open(directory).notebooks == ("analysis.ipynb",)


class TestChoosingTheSnapshot:
    def test_defaults_to_the_most_recently_frozen(self, args, tmp_path):
        # Not the last by name: an id is <date>-<hash>, so same-day snapshots
        # sort arbitrarily. The manifest's timestamp decides.
        new_experiment.main(["sfo-bos"] + args)

        experiment = Experiment.open(tmp_path / "experiments" / "sfo-bos")
        assert experiment.snapshot.snapshot_id == "2026-09-11-newer"

    def test_an_id_can_be_named(self, args, tmp_path):
        new_experiment.main(["sfo-bos", "--snapshot", "2026-09-10-older"] + args)

        experiment = Experiment.open(tmp_path / "experiments" / "sfo-bos")
        assert experiment.snapshot.snapshot_id == "2026-09-10-older"

    def test_a_path_can_be_named(self, args, tmp_path, snapshots):
        new_experiment.main(
            ["sfo-bos", "--snapshot", str(snapshots / "2026-09-10-older")] + args
        )

        experiment = Experiment.open(tmp_path / "experiments" / "sfo-bos")
        assert experiment.snapshot.snapshot_id == "2026-09-10-older"

    def test_an_unknown_snapshot_raises(self, args):
        with pytest.raises(FileNotFoundError, match="nope"):
            new_experiment.main(["sfo-bos", "--snapshot", "nope"] + args)

    def test_no_snapshots_at_all_says_what_to_do(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="make snapshot"):
            new_experiment.main([
                "sfo-bos",
                "--root", str(tmp_path / "experiments"),
                "--snapshot-root", str(tmp_path / "empty"),
            ])


class TestNotClobbering:
    def test_refuses_to_overwrite(self, args, tmp_path, capsys):
        new_experiment.main(["sfo-bos"] + args)
        edited = tmp_path / "experiments" / "sfo-bos" / "experiment.toml"
        edited.write_text(edited.read_text() + '\nnote = "mine"\n')

        status = new_experiment.main(["sfo-bos"] + args)

        assert status == 1
        assert "already exists" in capsys.readouterr().err
        assert "mine" in edited.read_text()

    def test_force_overwrites(self, args, tmp_path):
        new_experiment.main(["sfo-bos"] + args)
        edited = tmp_path / "experiments" / "sfo-bos" / "experiment.toml"
        edited.write_text(edited.read_text() + '\nnote = "mine"\n')

        assert new_experiment.main(["sfo-bos", "--force"] + args) == 0
        assert "mine" not in edited.read_text()

    def test_force_does_not_touch_the_notebook(self, args, tmp_path):
        # --force regenerates the config, which this script owns. A notebook
        # is the experimenter's work and is never overwritten.
        new_experiment.main(["sfo-bos"] + args)
        notebook = tmp_path / "experiments" / "sfo-bos" / "explore.ipynb"
        notebook.write_text('{"cells": [], "nbformat": 4, "nbformat_minor": 5}')

        new_experiment.main(["sfo-bos", "--force"] + args)

        assert json.loads(notebook.read_text())["cells"] == []
