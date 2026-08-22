"""Commercial aircraft performance model used by the flight simulator."""

import math
from atomosphere import InternationalStandardAtmosphere

class CommercialAircraft:
    """Aircraft performance configuration and force/fuel-flow calculations."""

    def __init__(self, model_name, oew, max_payload, max_fuel, wing_area, cd0, k, mach_crit, max_thrust_sl, tsfc_sl):
        """Initialize the aircraft's static performance parameters.

        Args:
            model_name: Human-readable aircraft type designation.
            oew: Operating Empty Weight (kg).
            max_payload: Payload capacity (kg).
            max_fuel: Max fuel weight (kg).
            wing_area: Wing reference area (m^2).
            cd0: Zero-lift parasite drag coefficient.
            k: Induced drag factor (1 / (pi * AR * e)).
            mach_crit: Critical Mach number for wave drag onset.
            max_thrust_sl: Max thrust at sea level (N).
            tsfc_sl: Thrust-specific fuel consumption at sea level (kg/N/s).
        """
        self.model_name = model_name
        self.oew = oew                   # Operating Empty Weight (kg)
        self.max_payload = max_payload   # Payload capacity (kg)
        self.max_fuel = max_fuel         # Max fuel weight (kg)
        self.S = wing_area               # Wing reference area (m^2)
        self.cd0 = cd0                   # Zero-lift parasite drag coefficient
        self.k = k                       # Induced drag factor (1 / (pi * AR * e))
        self.mach_crit = mach_crit       # Critical Mach number for wave drag
        self.max_thrust_sl = max_thrust_sl # Max thrust at sea level (N)
        self.tsfc_sl = tsfc_sl           # Thrust-specific fuel consumption at SL (kg/N/s)

    @classmethod
    def get_preset(cls, aircraft_type):
        """Build a preset instance for a standard commercial aircraft type.

        Args:
            aircraft_type: One of ``"A321neo"``, ``"B737-800"``, ``"B787-9"``.

        Returns:
            A configured `CommercialAircraft` instance. Falls back to the
            ``"A321neo"`` preset if `aircraft_type` is not recognized.
        """
        presets = {
            "A321neo": cls("A321neo", 50000, 25000, 23000, 122.6, 0.018, 0.040, 0.78, 280000, 1.1e-5),
            "B737-800": cls("B737-800", 41413, 20542, 20894, 124.6, 0.019, 0.042, 0.78, 240000, 1.2e-5),
            "B787-9": cls("B787-9", 128850, 52500, 101000, 377.0, 0.015, 0.035, 0.85, 640000, 0.95e-5),
        }
        return presets.get(aircraft_type, presets["A321neo"])

    def calculate_forces(self, mass, altitude_m, tas_m_s, climb_angle_rad=0.0):
        """Calculate lift, drag, available thrust, and fuel flow for a flight state.

        Args:
            mass: Current aircraft mass (kg).
            altitude_m: Pressure altitude (m).
            tas_m_s: True airspeed (m/s).
            climb_angle_rad: Flight path angle relative to horizontal (rad).
                Positive for climb, negative for descent, defaults to level flight.

        Returns:
            A dict with keys ``lift``, ``drag``, ``max_thrust``, ``tsfc``,
            ``mach``, and ``q``, all in SI units.
        """
        g = InternationalStandardAtmosphere.G0
        temp, press, rho, a = InternationalStandardAtmosphere.get_properties(altitude_m)
        mach = tas_m_s / a

        # Lift & Dynamic Pressure
        q = 0.5 * rho * (tas_m_s ** 2)
        weight = mass * g
        lift = weight * math.cos(climb_angle_rad)
        cL = lift / (q * self.S) if q > 0 else 0.0

        # Drag Polar + Wave Drag correction past critical Mach
        wave_drag = 0.0
        if mach > self.mach_crit:
            wave_drag = 20.0 * (mach - self.mach_crit) ** 4

        cD = self.cd0 + self.k * (cL ** 2) + wave_drag
        drag = cD * q * self.S

        # Thrust decay with altitude (rho / rho0)^0.7
        thrust_avail = self.max_thrust_sl * ((rho / InternationalStandardAtmosphere.RHO0) ** 0.7)

        # TSFC scaling with Mach
        tsfc = self.tsfc_sl * (1.0 + 0.5 * mach)

        return {
            "lift": lift,
            "drag": drag,
            "max_thrust": thrust_avail,
            "tsfc": tsfc,
            "mach": mach,
            "q": q
        }

