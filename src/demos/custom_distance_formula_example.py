"""Example: plugging in a brand-new DistanceFormula.

Adds an `Equirectangular` formula without touching `Point`, `Haversine`, or
`Vincenty`.

Run from anywhere:
    uv run python src/demos/custom_distance_formula_example.py
"""


from math import radians, cos

from flight_planner import Airport
from flight_planner.geo import DistanceFormula, Haversine, Vincenty

_EARTH_RADIUS_KM = 6371.0


class Equirectangular(DistanceFormula):
    """Flat-plane approximation with a latitude correction factor.

    Very fast, but only accurate for points close together — accuracy
    degrades rapidly over long-haul distances. Included as an example of
    adding a new DistanceFormula: implement calculate(), nothing else
    changes in Point/Haversine/Vincenty/AStar.
    """

    def calculate(self, a: Airport, b: Airport) -> float:
        """Compute the flat-plane approximate distance between two points.

        Args:
            a: First point.
            b: Second point.

        Returns:
            Distance in kilometers. Accurate only over short distances.
        """
        lat1, lon1 = radians(a.latitude), radians(a.longitude)
        lat2, lon2 = radians(b.latitude), radians(b.longitude)
        x = (lon2 - lon1) * cos((lat1 + lat2) / 2)
        y = lat2 - lat1
        return _EARTH_RADIUS_KM * (x ** 2 + y ** 2) ** 0.5


if __name__ == "__main__":
    jfk = Airport("JFK", city="New York", latitude=40.6413, longitude=-73.7781)
    ord_ = Airport("ORD", city="Chicago", latitude=41.9742, longitude=-87.9073)

    for name, formula in [("Haversine", Haversine()), ("Vincenty", Vincenty()), ("Equirectangular", Equirectangular())]:
        print(f"{name:>15}: {jfk.distance_to(ord_, formula):.2f} km")

    print("\nAll three implement the same DistanceFormula.calculate(a, b) "
          "interface, so any of them can be passed to Point.distance_to() "
          "or into an AStar heuristic unchanged.")
