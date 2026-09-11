from pathlib import Path

import matplotlib
import pytest

# Use a non-interactive backend so plotting code under test never tries to
# open a GUI window during the test run.
matplotlib.use("Agg")


@pytest.fixture(scope="session")
def processed_data_dir() -> Path:
    """Return the repository's processed-data directory.

    The `flight_planner` package takes CSV paths from its caller and knows
    nothing about the repository layout, so locating the real data is the
    test suite's job rather than the package's.

    Returns:
        Absolute `Path` to `data/processed`.
    """
    return Path(__file__).resolve().parents[1] / "data" / "processed"


@pytest.fixture(scope="session")
def airports_csv(processed_data_dir: Path) -> Path:
    """Return the processed `airports.csv` file.

    Returns:
        Absolute `Path` to the airports CSV.
    """
    return processed_data_dir / "airports.csv"


@pytest.fixture(scope="session")
def routes_csv(processed_data_dir: Path) -> Path:
    """Return the processed `routes.csv` file.

    Returns:
        Absolute `Path` to the routes CSV.
    """
    return processed_data_dir / "routes.csv"
