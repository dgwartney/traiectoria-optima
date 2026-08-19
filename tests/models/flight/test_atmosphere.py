import math

import pytest

from atomosphere import InternationalStandardAtmosphere as ISA


def test_sea_level_properties_match_iso_2533_constants():
    temp, press, rho, a = ISA.get_properties(0.0)

    assert temp == pytest.approx(ISA.T0)
    assert press == pytest.approx(ISA.P0)
    assert rho == pytest.approx(ISA.RHO0, rel=1e-3)
    assert a == pytest.approx(340.3, rel=1e-2)


def test_temperature_decreases_linearly_in_the_troposphere():
    temp_0, _, _, _ = ISA.get_properties(0.0)
    temp_5000, _, _, _ = ISA.get_properties(5000.0)

    expected = temp_0 - ISA.LAPSE_RATE * 5000.0
    assert temp_5000 == pytest.approx(expected)


def test_properties_are_continuous_at_the_tropopause_boundary():
    _, press_below, _, _ = ISA.get_properties(ISA.H_TROPO - 1e-3)
    _, press_at, _, _ = ISA.get_properties(ISA.H_TROPO)

    assert press_below == pytest.approx(press_at, rel=1e-4)


def test_density_decreases_monotonically_with_altitude():
    altitudes = [0, 1000, 5000, 11000, 15000, 20000]
    densities = [ISA.get_properties(alt)[2] for alt in altitudes]

    assert densities == sorted(densities, reverse=True)


def test_speed_of_sound_matches_ideal_gas_relation():
    temp, _, _, a = ISA.get_properties(8000.0)
    expected = math.sqrt(ISA.GAMMA * ISA.R * temp)
    assert a == pytest.approx(expected)
