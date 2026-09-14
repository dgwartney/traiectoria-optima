"""Great-circle interpolation, and the dateline it has to survive.

`Geodesic` is the one place in `viz` that does geometry, so it is tested
directly rather than through a rendered map. The dateline cases use real
coordinates from the committed world snapshot: the bug they guard against is
invisible on a US-only network, which is exactly why it needs a test.
"""

import pytest

# Geometry needs pyproj, which lives in the `notebooks` dependency group
# rather than `dev` -- the same reason the other viz modules skip on folium.
pytest.importorskip("pyproj")

from flight_planner import Airport
from flight_planner.viz import Geodesic

# Real positions, rounded, from data/snapshots/2026-09-11-bb90a8.
AKL = Airport("AKL", latitude=-37.008, longitude=174.792)
LAX = Airport("LAX", latitude=33.943, longitude=-118.408)
SFO = Airport("SFO", latitude=37.619, longitude=-122.375)
BOS = Airport("BOS", latitude=42.364, longitude=-71.005)


def jumps(points):
    """Count consecutive longitudes more than 180 degrees apart.

    A single such jump is what makes Leaflet draw a line back across the whole
    map, so this is the property the unwrapping exists to keep at zero.

    Args:
        points: Sequence of `[lat, lon]` pairs.

    Returns:
        Number of offending steps.
    """
    return sum(
        1
        for before, after in zip(points, points[1:])
        if abs(after[1] - before[1]) > 180
    )


class TestHowManyPointsItReturns:
    def test_it_returns_the_interpolated_points_plus_both_endpoints(self):
        assert len(Geodesic(segments=6).between(SFO, BOS)) == 8

    def test_the_segment_count_is_configurable(self):
        assert len(Geodesic(segments=24).between(SFO, BOS)) == 26

    def test_it_starts_at_the_origin_and_ends_at_the_destination(self):
        points = Geodesic(segments=6).between(SFO, BOS)

        assert points[0] == pytest.approx([SFO.latitude, SFO.longitude])
        assert points[-1] == pytest.approx([BOS.latitude, BOS.longitude])


class TestTheCurveItDraws:
    def test_it_bows_away_from_the_straight_line(self):
        # The whole point of interpolating: a great circle between two
        # mid-latitude airports passes north of the straight Mercator line.
        points = Geodesic(segments=6).between(SFO, BOS)
        midpoint_lat = (SFO.latitude + BOS.latitude) / 2

        assert max(lat for lat, _ in points) > midpoint_lat


class TestTheDateline:
    def test_it_unwraps_rather_than_jumping_the_antimeridian(self):
        assert jumps(Geodesic(segments=8).between(AKL, LAX)) == 0

    def test_it_carries_longitudes_past_180_to_do_so(self):
        # Deliberately outside [-180, 180]: that is what keeps the line
        # continuous, and why a layer has to report the points it drew rather
        # than let the map infer them from airport positions.
        longitudes = [lon for _, lon in Geodesic(segments=8).between(AKL, LAX)]

        assert max(longitudes) > 180

    def test_it_leaves_ordinary_routes_inside_the_normal_range(self):
        longitudes = [lon for _, lon in Geodesic(segments=8).between(SFO, BOS)]

        assert all(-180 <= lon <= 180 for lon in longitudes)

    def test_it_unwraps_westward_too(self):
        assert jumps(Geodesic(segments=8).between(LAX, AKL)) == 0


#: Route rows in the committed world snapshot whose shorter great circle
#: crosses the antimeridian, and the undirected airport pairs they collapse
#: to. Report §8.3 states both.
CROSSING_ROWS = 647
CROSSING_PAIRS = 137


@pytest.fixture(scope="module")
def crossings(repo_root):
    """Every snapshot route whose shorter arc crosses the antimeridian."""
    from flight_planner.experiments import Snapshot

    planner = (
        Snapshot.open(repo_root / "data" / "snapshots" / "2026-09-11-bb90a8")
        .catalog()
        .planner()
    )

    return [
        edge
        for edge in planner.edges
        if abs(edge.origin.longitude - edge.destination.longitude) > 180
    ]


class TestTheRealNetworkSuppliesTheDatelineCase:
    """The snapshot contains these routes, and all of them draw continuously.

    Report §8.3 states the count. The unwrapping tests above use two
    hand-picked airports, which proves the algorithm; this proves the
    algorithm is needed -- and that no route in the committed world snapshot
    defeats it.
    """

    def test_the_snapshot_contains_them(self, crossings):
        pairs = {
            frozenset((e.origin.iata_code, e.destination.iata_code))
            for e in crossings
        }

        assert len(crossings) == CROSSING_ROWS
        assert len(pairs) == CROSSING_PAIRS

    def test_every_one_of_them_draws_as_a_continuous_line(self, crossings):
        """Zero jumps across 647 real routes, not just the two tested above."""
        geodesic = Geodesic(segments=6)

        offenders = [
            f"{e.origin.iata_code}->{e.destination.iata_code}"
            for e in crossings
            if jumps(geodesic.between(e.origin, e.destination))
        ]

        assert offenders == []
