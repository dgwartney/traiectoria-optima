"""Vincenty geodesic distance formula on the WGS-84 ellipsoid."""

from __future__ import annotations
from math import radians, sin, cos, atan2, sqrt
from typing import TYPE_CHECKING

from distance.formula import DistanceFormula

if TYPE_CHECKING:
    from point import Point

# WGS-84 ellipsoid parameters (km)
_SEMI_MAJOR_AXIS_KM = 6378.137
_FLATTENING = 1 / 298.257223563
_SEMI_MINOR_AXIS_KM = (1 - _FLATTENING) * _SEMI_MAJOR_AXIS_KM

_MAX_ITERATIONS = 200
_CONVERGENCE_THRESHOLD = 1e-12


class Vincenty(DistanceFormula):
    """Iterative geodesic distance on the WGS-84 oblate ellipsoid.

    Millimeter-accurate for standard coordinate pairs. Known limitation
    (not handled here): the iteration can fail to converge for
    near-antipodal points, in which case a ValueError is raised.
    """

    def calculate(self, a: "Point", b: "Point") -> float:
        """Compute the geodesic distance between two points.

        Args:
            a: First point.
            b: Second point.

        Returns:
            Distance in kilometers on the WGS-84 ellipsoid.

        Raises:
            ValueError: If the iteration does not converge, which happens for
                near-antipodal points.
        """
        if a.latitude == b.latitude and a.longitude == b.longitude:
            return 0.0

        lat1, lat2 = radians(a.latitude), radians(b.latitude)
        big_l = radians(b.longitude - a.longitude)

        reduced_lat1 = atan2((1 - _FLATTENING) * sin(lat1), cos(lat1))
        reduced_lat2 = atan2((1 - _FLATTENING) * sin(lat2), cos(lat2))
        sin_r1, cos_r1 = sin(reduced_lat1), cos(reduced_lat1)
        sin_r2, cos_r2 = sin(reduced_lat2), cos(reduced_lat2)

        lam = big_l
        for _ in range(_MAX_ITERATIONS):
            sin_lam, cos_lam = sin(lam), cos(lam)
            sin_sigma = sqrt(
                (cos_r2 * sin_lam) ** 2
                + (cos_r1 * sin_r2 - sin_r1 * cos_r2 * cos_lam) ** 2
            )
            if sin_sigma == 0:
                return 0.0  # coincident points

            cos_sigma = sin_r1 * sin_r2 + cos_r1 * cos_r2 * cos_lam
            sigma = atan2(sin_sigma, cos_sigma)

            sin_alpha = cos_r1 * cos_r2 * sin_lam / sin_sigma
            cos_sq_alpha = 1 - sin_alpha ** 2
            cos_2sigma_m = (
                cos_sigma - 2 * sin_r1 * sin_r2 / cos_sq_alpha
                if cos_sq_alpha != 0
                else 0.0
            )

            c = _FLATTENING / 16 * cos_sq_alpha * (4 + _FLATTENING * (4 - 3 * cos_sq_alpha))
            prev_lam = lam
            lam = big_l + (1 - c) * _FLATTENING * sin_alpha * (
                sigma
                + c * sin_sigma * (cos_2sigma_m + c * cos_sigma * (-1 + 2 * cos_2sigma_m ** 2))
            )
            if abs(lam - prev_lam) < _CONVERGENCE_THRESHOLD:
                break
        else:
            raise ValueError("Vincenty formula failed to converge (likely near-antipodal points).")

        u_sq = cos_sq_alpha * (_SEMI_MAJOR_AXIS_KM ** 2 - _SEMI_MINOR_AXIS_KM ** 2) / _SEMI_MINOR_AXIS_KM ** 2
        big_a = 1 + u_sq / 16384 * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)))
        big_b = u_sq / 1024 * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))
        delta_sigma = big_b * sin_sigma * (
            cos_2sigma_m
            + big_b
            / 4
            * (
                cos_sigma * (-1 + 2 * cos_2sigma_m ** 2)
                - big_b
                / 6
                * cos_2sigma_m
                * (-3 + 4 * sin_sigma ** 2)
                * (-3 + 4 * cos_2sigma_m ** 2)
            )
        )

        return _SEMI_MINOR_AXIS_KM * big_a * (sigma - delta_sigma)
