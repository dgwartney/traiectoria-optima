"""Describing the machine a measurement was taken on, and taking it.

A node count reproduces anywhere: `Dijkstra` expands 746 vertices on the
SFO-BOS query on any computer ever built. A millisecond does not. So a
recorded result that contains timings has to say what it ran on, or the number
means nothing to the next reader — including the same reader six months later
on different hardware.

`experiments/search-cost` established that convention and carries its own
inline copy of `environment`, written before this module existed. This is the
shared version; that notebook is left alone rather than edited from a
different branch.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List


def environment() -> Dict[str, Any]:
    """Describe the machine, so a timing here is comparable with one elsewhere.

    Returns:
        Mapping of CPU model, core count, platform, Python version, and
        whether this is a Colab runtime. Every value is JSON-serializable, so
        it can go straight into `Experiment.record`.
    """
    cpu = platform.processor() or platform.machine()
    if platform.system() == "Darwin":
        probe = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            check=False,
        )
        cpu = probe.stdout.strip() or cpu
    elif Path("/proc/cpuinfo").exists():  # Linux, including Colab
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break

    try:
        # find_spec raises rather than returning None when the parent package
        # `google` is absent, which is the normal case off Colab.
        colab = importlib.util.find_spec("google.colab") is not None
    except ModuleNotFoundError:
        colab = False

    return {
        "cpu": cpu,
        "cores": os.cpu_count(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "colab": colab,
    }


def median_ms(work: Callable[[], Any], repeats: int = 5) -> float:
    """Time `work` repeatedly and return the median in milliseconds.

    The median, not the mean: a single scheduling hiccup on a laptop moves a
    mean by more than the difference these experiments are trying to measure.
    One untimed warm-up run comes first, so the figure does not include
    whatever the first call populates — memoized distances, import side
    effects, a cold cache line.

    Args:
        work: Callable taking no arguments. Its return value is discarded.
        repeats: How many timed runs to take. Must be at least one.

    Returns:
        Median elapsed time in milliseconds.

    Raises:
        ValueError: If `repeats` is less than one.
    """
    if repeats < 1:
        raise ValueError("repeats must be at least 1")

    work()  # warm-up, discarded

    samples: List[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        work()
        samples.append((time.perf_counter() - started) * 1000.0)
    return statistics.median(samples)
