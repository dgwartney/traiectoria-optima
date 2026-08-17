import math

class InternationalStandardAtmosphere:
    """Calculates atmospheric properties given pressure altitude (meters)."""
    R = 287.058          # Specific gas constant for dry air (J/kg*K)
    G0 = 9.80665         # Standard gravity (m/s^2)
    GAMMA = 1.4          # Heat capacity ratio
    T0 = 288.15          # Sea level standard temperature (K)
    P0 = 101325.0        # Sea level standard pressure (Pa)
    RHO0 = 1.225         # Sea level density (kg/m^3)
    LAPSE_RATE = 0.0065  # Troposphere temperature lapse rate (K/m)
    H_TROPO = 11000.0    # Tropopause height (m)

    @classmethod
    def get_properties(cls, altitude_m):
        """Returns (temperature_K, pressure_Pa, density_kg_m3, speed_of_sound_m_s)."""
        if altitude_m <= cls.H_TROPO:
            temp = cls.T0 - cls.LAPSE_RATE * altitude_m
            press = cls.P0 * (temp / cls.T0) ** (cls.G0 / (cls.LAPSE_RATE * cls.R))
        else:
            temp = cls.T0 - cls.LAPSE_RATE * cls.H_TROPO
            p_tropo = cls.P0 * (temp / cls.T0) ** (cls.G0 / (cls.LAPSE_RATE * cls.R))
            press = p_tropo * math.exp(-cls.G0 * (altitude_m - cls.H_TROPO) / (cls.R * temp))

        density = press / (cls.R * temp)
        speed_of_sound = math.sqrt(cls.GAMMA * cls.R * temp)
        return temp, press, density, speed_of_sound
