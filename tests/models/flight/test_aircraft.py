import pytest

from aircraft import CommercialAircraft
from atomosphere import InternationalStandardAtmosphere as ISA


@pytest.mark.parametrize("preset_name", ["A321neo", "B737-800", "B787-9"])
def test_get_preset_returns_matching_model_name(preset_name):
    aircraft = CommercialAircraft.get_preset(preset_name)
    assert aircraft.model_name == preset_name


def test_get_preset_falls_back_to_a321neo_for_unknown_type():
    aircraft = CommercialAircraft.get_preset("does-not-exist")
    assert aircraft.model_name == "A321neo"


def test_calculate_forces_at_zero_airspeed_has_no_dynamic_pressure():
    aircraft = CommercialAircraft.get_preset("A321neo")
    forces = aircraft.calculate_forces(mass=70000, altitude_m=0.0, tas_m_s=0.0)

    assert forces["q"] == 0.0
    # cD reduces to cd0 when cL is forced to 0 by the q == 0 guard.
    assert forces["mach"] == 0.0


def test_thrust_available_at_sea_level_equals_rated_max_thrust():
    aircraft = CommercialAircraft.get_preset("A321neo")
    forces = aircraft.calculate_forces(mass=70000, altitude_m=0.0, tas_m_s=200.0)

    assert forces["max_thrust"] == pytest.approx(aircraft.max_thrust_sl, rel=1e-3)


def test_thrust_available_decreases_with_altitude():
    aircraft = CommercialAircraft.get_preset("A321neo")
    sea_level = aircraft.calculate_forces(mass=70000, altitude_m=0.0, tas_m_s=200.0)
    cruise = aircraft.calculate_forces(mass=70000, altitude_m=11000.0, tas_m_s=230.0)

    assert cruise["max_thrust"] < sea_level["max_thrust"]


def test_wave_drag_only_kicks_in_above_critical_mach():
    aircraft = CommercialAircraft.get_preset("A321neo")
    _, _, _, a = ISA.get_properties(11000.0)

    below_crit = aircraft.calculate_forces(
        mass=70000, altitude_m=11000.0, tas_m_s=(aircraft.mach_crit - 0.05) * a
    )
    above_crit = aircraft.calculate_forces(
        mass=70000, altitude_m=11000.0, tas_m_s=(aircraft.mach_crit + 0.05) * a
    )

    assert below_crit["drag"] < above_crit["drag"]


def test_lift_scales_with_climb_angle_cosine():
    import math

    aircraft = CommercialAircraft.get_preset("A321neo")
    level = aircraft.calculate_forces(mass=70000, altitude_m=5000.0, tas_m_s=200.0)
    climbing = aircraft.calculate_forces(
        mass=70000, altitude_m=5000.0, tas_m_s=200.0, climb_angle_rad=math.radians(10)
    )

    assert climbing["lift"] == pytest.approx(level["lift"] * math.cos(math.radians(10)))
