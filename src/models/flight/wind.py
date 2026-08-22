"""Interpolated atmospheric wind field and wind-triangle calculations."""

import numpy as np
import scipy.interpolate as interpolate

class AtmosphericWindModel:
    """Interpolates a 3D global atmospheric wind field.

    Wraps two `scipy.interpolate.RegularGridInterpolator` instances (one per
    wind component) over a (altitude, latitude, longitude) grid.
    """

    def __init__(self, lats, lons, alt_m, u_wind_grid, v_wind_grid):
        """Build the interpolators from a regular wind grid.

        Args:
            lats: 1D array of grid latitudes (deg).
            lons: 1D array of grid longitudes (deg).
            alt_m: 1D array of altitudes (m).
            u_wind_grid: 3D array shaped ``(len(alt), len(lat), len(lon))``
                of East-West wind component (m/s).
            v_wind_grid: 3D array shaped ``(len(alt), len(lat), len(lon))``
                of North-South wind component (m/s).
        """
        self.interp_u = interpolate.RegularGridInterpolator(
            (alt_m, lats, lons), u_wind_grid, bounds_error=False, fill_value=0.0
        )
        self.interp_v = interpolate.RegularGridInterpolator(
            (alt_m, lats, lons), v_wind_grid, bounds_error=False, fill_value=0.0
        )

    def get_wind_components(self, lat, lon, altitude_m):
        """Look up the wind vector at a point.

        Args:
            lat: Latitude (deg).
            lon: Longitude (deg).
            altitude_m: Altitude (m).

        Returns:
            A tuple ``(u, v)`` of eastward and northward wind velocity (m/s).
        """
        point = np.array([altitude_m, lat, lon])
        u = float(self.interp_u(point)[0])
        v = float(self.interp_v(point)[0])
        return u, v

    def calculate_headwind_and_groundspeed(self, lat, lon, altitude_m, heading_rad, tas_m_s):
        """Solve the wind triangle for groundspeed, drift, and wind components.

        Args:
            lat: Latitude (deg).
            lon: Longitude (deg).
            altitude_m: Altitude (m).
            heading_rad: True heading relative to true north (rad).
            tas_m_s: True airspeed (m/s).

        Returns:
            A dict with keys ``headwind_m_s`` (positive = headwind),
            ``crosswind_m_s`` (positive = from the right), ``drift_angle_deg``,
            and ``groundspeed_m_s``.
        """
        u, v = self.get_wind_components(lat, lon, altitude_m)
        
        # Wind velocity vector components
        w_e = u  # East component
        w_n = v  # North component

        # Aircraft heading unit vectors
        heading_e = np.sin(heading_rad)
        heading_n = np.cos(heading_rad)

        # Headwind (+ = headwind, - = tailwind)
        headwind = -(w_e * heading_e + w_n * heading_n)
        
        # Crosswind (+ = from right, - = from left)
        crosswind = -w_e * heading_n + w_n * heading_e

        # Drift angle (crab angle) compensation to maintain track
        sin_drift = crosswind / tas_m_s
        sin_drift = np.clip(sin_drift, -1.0, 1.0)
        drift_angle = np.arcsin(sin_drift)

        # Effective groundspeed along intended course line
        groundspeed = tas_m_s * np.cos(drift_angle) - headwind
        
        return {
            "headwind_m_s": headwind,
            "crosswind_m_s": crosswind,
            "drift_angle_deg": np.degrees(drift_angle),
            "groundspeed_m_s": max(0.0, groundspeed)
        }