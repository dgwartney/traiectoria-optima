"""Charts for the search-cost experiment.

Kept out of `flight_planner` on purpose: the wheel depends on `pandas` and
nothing else, while `matplotlib` is a `dev`-group dependency. Plotting is
something this repository does, not something the package offers.

Two charts, because the data asks two questions:

- `runtime_vs_size` — how each algorithm scales. Log-log, so the growth
  exponent reads as a slope rather than a curve, which is what the complexity
  write-up needs.
- `nodes_expanded` — how much work each does on a fixed graph. Linear, because
  A*'s bars being nearly invisible beside Dijkstra's *is* the finding.

Colours are the first three slots of a categorical palette validated for
colour-vision deficiency against both surfaces (worst all-pairs CVD dE 9.4,
normal-vision dE 20.9, contrast >= 3:1 on the dark surface). They are assigned
by algorithm identity and never cycled, so adding a fourth algorithm cannot
repaint the three already on screen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")  # no display in a notebook run or a test
import matplotlib.pyplot as plt  # noqa: E402

# Slot 1 blue, slot 2 orange, slot 3 aqua -- stepped per surface, not flipped.
SERIES_COLOURS: Dict[str, Dict[str, str]] = {
    "dark": {"BFS": "#3987e5", "Dijkstra": "#d95926", "A*": "#199e70"},
    "light": {"BFS": "#2a78d6", "Dijkstra": "#eb6834", "A*": "#1baf7a"},
}

# Identity must survive greyscale printing and colour-blind readers, so each
# series carries a marker shape as well as a hue.
SERIES_MARKERS: Dict[str, str] = {"BFS": "o", "Dijkstra": "s", "A*": "^"}

SURFACE: Dict[str, Dict[str, str]] = {
    # #1a1a19 is effectively the reveal.js black theme's background.
    "dark": {"bg": "#1a1a19", "ink": "#ffffff", "muted": "#c3c2b7", "grid": "#3a3a38"},
    "light": {"bg": "#fcfcfb", "ink": "#0b0b0b", "muted": "#52514e", "grid": "#d8d7d2"},
}

ORDER = ("BFS", "Dijkstra", "A*")


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


def runtime_vs_size(series: Sequence[Mapping], destination, mode: str = "dark") -> Path:
    """Plot median query time against graph size, one line per algorithm.

    Log-log: the sizes span roughly thirty-fold, and a power law reads as a
    straight line whose slope is the growth exponent.

    Args:
        series: One mapping per size, with `size` (V+E), `label`, and a
            `median_ms` mapping of algorithm name to milliseconds.
        destination: Path to write the PNG to.
        mode: `"dark"` for the deck, `"light"` for the report.

    Returns:
        The path written.
    """
    figure, axes, palette, surface = _style(mode)

    ordered = sorted(series, key=lambda row: row["size"])
    sizes = [row["size"] for row in ordered]

    for name in ORDER:
        times = [row["median_ms"][name] for row in ordered]
        axes.plot(
            sizes,
            times,
            label=name,
            color=palette[name],
            marker=SERIES_MARKERS[name],
            markersize=8,
            linewidth=2,
        )
        # Direct labels as well as a legend, so identity is never colour alone.
        axes.annotate(
            name,
            xy=(sizes[-1], times[-1]),
            xytext=(8, 0),
            textcoords="offset points",
            color=palette[name],
            fontsize=11,
            va="center",
        )

    axes.set_xscale("log")
    axes.set_yscale("log")
    axes.set_xlabel("graph size  (V + E)", color=surface["muted"], fontsize=11, labelpad=10)
    axes.set_ylabel("median query time (ms)", color=surface["muted"], fontsize=11, labelpad=10)
    axes.set_title(
        "Query time against graph size",
        color=surface["ink"],
        fontsize=14,
        fontweight="bold",
        pad=15,
        loc="left",
    )
    legend = axes.legend(frameon=False, loc="upper left", fontsize=10)
    for text in legend.get_texts():
        text.set_color(surface["muted"])

    axes.margins(x=0.12)
    return _save(figure, destination, surface)


def nodes_expanded(rows: Sequence[Mapping], destination, mode: str = "dark") -> Path:
    """Plot nodes expanded per query, grouped by algorithm.

    Linear rather than log: the point is how small A*'s bars are.

    Args:
        rows: One mapping per query, with `pair` and an `expanded` mapping of
            algorithm name to node count.
        destination: Path to write the PNG to.
        mode: `"dark"` for the deck, `"light"` for the report.

    Returns:
        The path written.
    """
    figure, axes, palette, surface = _style(mode)

    positions = range(len(rows))
    width = 0.26
    for offset, name in enumerate(ORDER):
        counts = [row["expanded"][name] for row in rows]
        bars = axes.bar(
            [p + (offset - 1) * width for p in positions],
            counts,
            width=width * 0.92,  # the gap is a surface-coloured spacer
            label=name,
            color=palette[name],
        )
        for bar, count in zip(bars, counts):
            axes.annotate(
                f"{count:,}",
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                color=surface["muted"],
            )

    axes.set_xticks(list(positions))
    axes.set_xticklabels([row["pair"] for row in rows], color=surface["muted"])
    axes.set_ylabel("nodes expanded", color=surface["muted"], fontsize=11, labelpad=10)
    axes.set_title(
        "Nodes expanded per query",
        color=surface["ink"],
        fontsize=14,
        fontweight="bold",
        pad=15,
        loc="left",
    )
    axes.grid(axis="x", visible=False)
    legend = axes.legend(frameon=False, loc="upper right", fontsize=10)
    for text in legend.get_texts():
        text.set_color(surface["muted"])

    return _save(figure, destination, surface)
