import numpy as np
import scipy.interpolate as interpolate

class AtmosphericWindModel:
    """
    Interpolates 3D/4D global atmospheric wind fields 
    (Latitude, Longitude, Altitude/Pressure Level, Time).
    """
    def __init__(self, lats, lons, alt_m, u_wind_grid, v_wind_grid):
        """
        lats: 1D array of grid latitudes [deg]
        lons: 1D array of grid longitudes [deg]
        alt_m: 1D array of altitudes [meters]
        u_wind_grid: 3D array (len(alt), len(lat), len(lon)) of East-West wind [m/s]
        v_wind_grid: 3D array (len(alt), len(lat), len(lon)) of North-South wind [m/s]
        """
        self.interp_u = interpolate.RegularGridInterpolator(
            (alt_m, lats, lons), u_wind_grid, bounds_error=False, fill_value=0.0
        )
        self.interp_v = interpolate.RegularGridInterpolator(
            (alt_m, lats, lons), v_wind_grid, bounds_error=False, fill_value=0.0
        )

    def get_wind_components(self, lat, lon, altitude_m):
        """Returns scalar U (eastward) and V (northward) wind velocity in m/s."""
        point = np.array([altitude_m, lat, lon])
        u = float(self.interp_u(point))
        v = float(self.interp_v(point))
        return u, v

    def calculate_headwind_and_groundspeed(self, lat, lon, altitude_m, heading_rad, tas_m_s):
        """
        Calculates groundspeed and drift angle accounting for wind vector drift.
        Heading_rad: True heading angle in radians relative to True North.
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