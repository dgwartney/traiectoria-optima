"""Charts for the graph-stats experiment.

Kept out of `flight_planner` on purpose, for the same reason
`experiments/search-cost/plots.py` is: the wheel depends on `pandas` and
nothing else, while `matplotlib` is a `dev`-group dependency. Plotting is
something this repository does, not something the package offers.

Two charts, because the statistics answer two different questions:

- `degree_distribution` -- what shape is the network? Log-log, because the
  answer is "heavy-tailed" and a linear histogram would hide that in a single
  bar at the origin.
- `top_hubs` -- which airports carry it? Linear bars with in- and out-degree
  paired, so the near-symmetry of scheduled aviation is visible rather than
  asserted.

Surfaces and dimensions are copied from `search-cost`'s module so that figures
from the two experiments sit side by side in the report and on a slide without
looking like they came from different projects. The categorical hues are not
copied: those are assigned by *algorithm identity* there, and this experiment
has no algorithms. It uses the two-series roles below instead.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")  # no display in a notebook run or a test
import matplotlib.pyplot as plt  # noqa: E402

# Slot 1 blue and slot 2 orange from the same validated categorical palette
# search-cost draws from, stepped per surface rather than flipped.
SERIES_COLOURS: Dict[str, Dict[str, str]] = {
    "dark": {"out": "#3987e5", "in": "#d95926"},
    "light": {"out": "#2a78d6", "in": "#eb6834"},
}

SURFACE: Dict[str, Dict[str, str]] = {
    # #1a1a19 is effectively the reveal.js black theme's background.
    "dark": {"bg": "#1a1a19", "ink": "#ffffff", "muted": "#c3c2b7", "grid": "#3a3a38"},
    "light": {"bg": "#fcfcfb", "ink": "#0b0b0b", "muted": "#52514e", "grid": "#d8d7d2"},
}


def _style(mode: str):
    """Create a figure and axes painted for the given surface.

    Args:
        mode: Either `"dark"` or `"light"`.

    Returns:
        Tuple of `(figure, axes, palette, surface)` ready to draw on.

    Raises:
        ValueError: If `mode` is not a known surface.
    """
    if mode not in SURFACE:
        raise ValueError(f"mode must be 'dark' or 'light', not {mode!r}")

    surface = SURFACE[mode]
    figure, axes = plt.subplots(figsize=(9, 5.5))
    # Both patches: a default-white axes box on a black slide is the classic
    # failure here, and it survives every other check.
    figure.patch.set_facecolor(surface["bg"])
    axes.set_facecolor(surface["bg"])

    for spine in ("top", "right"):
        axes.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        axes.spines[spine].set_color(surface["muted"])
    axes.tick_params(colors=surface["muted"], labelsize=10)
    axes.grid(True, linestyle=":", linewidth=0.8, color=surface["grid"], alpha=0.7)
    axes.set_axisbelow(True)

    return figure, axes, SERIES_COLOURS[mode], surface


def _save(figure, destination: Path, surface: Mapping[str, str]) -> Path:
    """Write a figure to disk at presentation resolution.

    Args:
        figure: The matplotlib figure to write.
        destination: Path to write to; parent directories are created.
        surface: Surface palette, for the saved background.

    Returns:
        The path written.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        destination,
        dpi=200,
        bbox_inches="tight",
        facecolor=surface["bg"],
        edgecolor="none",
    )
    plt.close(figure)
    return destination


def degree_distribution(counts: Mapping[int, int], destination, mode: str = "dark") -> Path:
    """Plot how many airports have each out-degree.

    Log-log on both axes. The distribution spans three orders of magnitude in
    both directions -- thousands of airports with one or two routes, one with
    915 -- so on linear axes every point but a handful collapses onto the
    origin. On log-log a power law reads as a straight line, which is the
    finding: the network is heavy-tailed, not uniform.

    Degree zero cannot be drawn on a log axis and is reported in the prose
    instead, where an airport with no departures deserves a sentence anyway.

    Args:
        counts: Mapping of out-degree to the number of airports having it.
        destination: Path to write the PNG to.
        mode: `"dark"` for the deck, `"light"` for the report.

    Returns:
        The path written.
    """
    figure, axes, palette, surface = _style(mode)

    plottable = sorted((degree, n) for degree, n in counts.items() if degree > 0)
    degrees = [degree for degree, _ in plottable]
    airports = [n for _, n in plottable]

    axes.scatter(
        degrees,
        airports,
        s=26,
        color=palette["out"],
        alpha=0.85,
        edgecolors="none",
    )

    axes.set_xscale("log")
    axes.set_yscale("log")
    axes.set_xlabel(
        "out-degree  (routes departing an airport)",
        color=surface["muted"],
        fontsize=11,
        labelpad=10,
    )
    axes.set_ylabel("airports", color=surface["muted"], fontsize=11, labelpad=10)
    axes.set_title(
        "How many airports have each out-degree",
        color=surface["ink"],
        fontsize=14,
        fontweight="bold",
        pad=15,
        loc="left",
    )

    return _save(figure, destination, surface)


def top_hubs(rows: Sequence[Mapping], destination, mode: str = "dark") -> Path:
    """Plot the busiest airports, in- and out-degree paired.

    Horizontal bars, because IATA codes read better as row labels than as
    rotated tick labels, and ordered busiest-first from the top.

    Args:
        rows: One mapping per airport, with `iata_code`, `out_degree` and
            `in_degree`. Drawn in the order given.
        destination: Path to write the PNG to.
        mode: `"dark"` for the deck, `"light"` for the report.

    Returns:
        The path written.
    """
    figure, axes, palette, surface = _style(mode)

    # Reversed, because a horizontal axis counts upward from the bottom and
    # the busiest airport belongs at the top.
    ordered = list(reversed(list(rows)))
    positions = range(len(ordered))
    height = 0.38

    for offset, (key, label) in enumerate((("out_degree", "out"), ("in_degree", "in"))):
        values = [row[key] for row in ordered]
        bars = axes.barh(
            [p + (offset - 0.5) * height for p in positions],
            values,
            height=height * 0.9,  # the gap is a surface-coloured spacer
            label=f"{label}-degree",
            color=palette[label],
        )
        for bar, value in zip(bars, values):
            axes.annotate(
                f"{value:,}",
                xy=(bar.get_width(), bar.get_y() + bar.get_height() / 2),
                xytext=(4, 0),
                textcoords="offset points",
                va="center",
                fontsize=9,
                color=surface["muted"],
            )

    axes.set_yticks(list(positions))
    axes.set_yticklabels([row["iata_code"] for row in ordered], color=surface["muted"])
    axes.set_xlabel("routes", color=surface["muted"], fontsize=11, labelpad=10)
    axes.set_title(
        f"The {len(ordered)} busiest airports",
        color=surface["ink"],
        fontsize=14,
        fontweight="bold",
        pad=15,
        loc="left",
    )
    axes.grid(axis="y", visible=False)
    axes.margins(x=0.12)
    legend = axes.legend(frameon=False, loc="lower right", fontsize=10)
    for text in legend.get_texts():
        text.set_color(surface["muted"])

    return _save(figure, destination, surface)
