"""The search-cost experiment's charts must keep rendering.

`plots.py` lives beside its notebook rather than in `flight_planner`, because
the wheel depends on `pandas` alone and `matplotlib` is a `dev`-group
dependency. That keeps it out of the package's own test tree, so it is covered
here with the other committed-experiment artifacts.

No `importorskip` guard: `tests/conftest.py` imports `matplotlib` at module
scope already, so the whole suite requires it and a guard here would be dead.

The charts are checked for the failures that are actually possible -- a file
that does not appear, an empty or non-PNG file, a background that is not the
surface it was asked for -- and not for their appearance. Layout is checked by
opening them, which is a human step the plan calls for explicitly.
"""

import importlib.util

import pytest

from flight_planner.experiments import Experiment

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# The two surfaces the same code has to serve: the reveal.js deck and the
# pandoc report. Keyed to plots.SURFACE.
MODES = ("dark", "light")


@pytest.fixture(scope="module")
def plots(repo_root):
    """Import the experiment's `plots.py` by path.

    `experiments/search-cost/` is a data directory, not a package -- and its
    name is not even a legal identifier -- so it cannot be imported by name.

    Args:
        repo_root: The repository root.

    Returns:
        The imported `plots` module.
    """
    path = repo_root / "experiments" / "search-cost" / "plots.py"
    spec = importlib.util.spec_from_file_location("search_cost_plots", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def recorded(repo_root):
    """Return the search-cost experiment's recorded results.

    The charts are smoke-tested against the real recorded data rather than a
    hand-built dict, so a change to the shape `record()` writes fails here too.
    Opened here rather than reusing `test_committed.py`'s fixture: that one is
    module-scoped and so not visible across files, and an experiment-specific
    fixture does not belong in the suite-wide `conftest.py`.

    Args:
        repo_root: The repository root.

    Returns:
        The `results` mapping from `results.json`.
    """
    experiment = Experiment.open(repo_root / "experiments" / "search-cost")
    return experiment.results()["results"]


class TestTheRuntimePlot:
    @pytest.mark.parametrize("mode", MODES)
    def test_it_writes_a_png_where_it_was_told_to(self, plots, recorded, tmp_path, mode):
        destination = tmp_path / "nested" / f"runtime-{mode}.png"

        written = plots.runtime_vs_size(recorded["runtime_series"], destination, mode=mode)

        assert written == destination
        assert destination.read_bytes()[:8] == PNG_MAGIC
        assert destination.stat().st_size > 10_000  # a blank axes is smaller

    def test_it_does_not_care_what_order_the_sizes_arrive_in(
        self, plots, recorded, tmp_path
    ):
        # The notebook happens to pass them ascending; the function sorts by
        # size itself, because a log-log line joined in list order would zigzag.
        series = recorded["runtime_series"]
        forward = plots.runtime_vs_size(series, tmp_path / "a.png").read_bytes()
        reversed_ = plots.runtime_vs_size(
            list(reversed(series)), tmp_path / "b.png"
        ).read_bytes()

        assert forward == reversed_


class TestTheNodesExpandedPlot:
    @pytest.mark.parametrize("mode", MODES)
    def test_it_writes_a_png_where_it_was_told_to(self, plots, recorded, tmp_path, mode):
        destination = tmp_path / "nested" / f"nodes-expanded-{mode}.png"

        written = plots.nodes_expanded(recorded["comparison"], destination, mode=mode)

        assert written == destination
        assert destination.read_bytes()[:8] == PNG_MAGIC
        assert destination.stat().st_size > 10_000


class TestTheSurfaces:
    def test_the_two_surfaces_render_differently(self, plots, recorded, tmp_path):
        # The whole point of the `mode` argument. If the surface tokens stopped
        # reaching the canvas, both files would come out identical.
        dark = plots.runtime_vs_size(
            recorded["runtime_series"], tmp_path / "dark.png", mode="dark"
        ).read_bytes()
        light = plots.runtime_vs_size(
            recorded["runtime_series"], tmp_path / "light.png", mode="light"
        ).read_bytes()

        assert dark != light

    def test_an_unknown_surface_is_refused_rather_than_guessed(
        self, plots, recorded, tmp_path
    ):
        with pytest.raises(ValueError, match="dark"):
            plots.runtime_vs_size(
                recorded["runtime_series"], tmp_path / "nope.png", mode="midnight"
            )

    def test_every_algorithm_has_a_colour_and_a_marker_on_both_surfaces(self, plots):
        # Identity must never rest on hue alone, and a series with no colour
        # assigned would raise a KeyError mid-render instead of here.
        for name in plots.ORDER:
            assert name in plots.SERIES_MARKERS
            for mode in MODES:
                assert name in plots.SERIES_COLOURS[mode]
