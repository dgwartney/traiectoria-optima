"""Every demo in `src/demos/` still runs against the current API.

`src/demos/` sits outside the wheel on purpose, so the demos exercise the
package's public re-exports the way a reader would. That also means nothing
imports them, and for most of the project nothing tested them either (#87) --
so a rename in `flight_planner` could leave a demo broken until someone ran it
by hand.

These are smoke tests: each module is executed in-process with `runpy`, as
`__main__` so the `if __name__ == "__main__"` body runs, and its output is
captured. Most of these demos have no `main()` -- the script *is* the guard
body -- which is why `runpy.run_path` is used rather than an import. Running is a low bar, but it is the bar that matters here,
because the failure being guarded against is an `AttributeError` on an API
that moved, not a wrong answer -- the demos that make claims worth checking
have their own files (`test_book_example.py`, `test_route_query_example.py`).

**What this cannot catch** is the defect that prompted it: `loader_example`
printed a header reading `OMA -> OMA` above a route from OMA to SJC, because
the f-string interpolated the departure twice. It ran perfectly. Only reading
the output found it, which is worth remembering before trusting a green suite
here -- hence `test_headings_name_the_query_they_report`.

Two modules are excluded and named, rather than silently skipped -- see
`WRITES_OUTSIDE_A_TEMP_DIR`.
"""

import contextlib
import io
import runpy
from pathlib import Path
from typing import List

import pytest

DEMOS_DIR = Path(__file__).resolve().parents[2] / "src" / "demos"

#: Demos excluded from the smoke run, with the reason. Empty: both experiment
#: demos were checked and write only into temporary directories, so they are
#: included. Kept as the documented place to put an exclusion, because a demo
#: quietly skipped is how this directory went untested in the first place.
WRITES_OUTSIDE_A_TEMP_DIR: List[str] = []


def demo_modules() -> List[str]:
    """Return every demo module name, in filename order."""
    return sorted(
        path.stem
        for path in DEMOS_DIR.glob("*.py")
        if path.stem != "__init__" and path.stem not in WRITES_OUTSIDE_A_TEMP_DIR
    )


MODULES = demo_modules()


def test_the_scan_finds_every_demo() -> None:
    """Appendix A says fourteen; a glob returning three would pass silently."""
    assert len(MODULES) == 14, f"expected 14 demo modules, found {MODULES}"


def run(name: str) -> str:
    """Execute one demo as `__main__` and return what it printed.

    Args:
        name: Module stem under `src/demos`.

    Returns:
        Everything the demo wrote to stdout.
    """
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        try:
            runpy.run_path(str(DEMOS_DIR / f"{name}.py"), run_name="__main__")
        except SystemExit as exit_:
            # `script_experiment_example` ends in `raise SystemExit(main())`.
            assert not exit_.code, f"{name} exited with status {exit_.code}"
    return captured.getvalue()


@pytest.mark.parametrize("name", MODULES)
def test_it_runs_and_prints_something(name: str) -> None:
    """Run the demo end to end and confirm it produced output."""
    assert run(name).strip(), f"{name} printed nothing"


def test_headings_name_the_query_they_report() -> None:
    """A heading must not name an airport the query below it does not use.

    The concrete regression: `loader_example` reported `OMA -> OMA` over a
    route from OMA to SJC. The demo ran, so a smoke test would have passed.
    """
    output = run("loader_example")

    assert "OMA -> SJC" in output
    assert "OMA -> OMA" not in output, (
        "a heading names the departure twice; the query underneath it does not"
    )
