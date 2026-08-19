import math

import numpy as np
import pytest

from wind import AtmosphericWindModel


@pytest.fixture
def calm_model():
    lats = np.array([-10.0, 0.0, 10.0])
    lons = np.array([-10.0, 0.0, 10.0])
    alts = np.array([0.0, 5000.0, 10000.0])
    zeros = np.zeros((len(alts), len(lats), len(lons)))
    return AtmosphericWindModel(lats, lons, alts, zeros, zeros)


@pytest.fixture
def uniform_easterly_model():
    """A wind field blowing uniformly from the west (positive U component)."""
    lats = np.array([-10.0, 0.0, 10.0])
    lons = np.array([-10.0, 0.0, 10.0])
    alts = np.array([0.0, 5000.0, 10000.0])
    u = np.full((len(alts), len(lats), len(lons)), 20.0)
    v = np.zeros((len(alts), len(lats), len(lons)))
    return AtmosphericWindModel(lats, lons, alts, u, v)


def test_get_wind_components_is_zero_in_calm_field(calm_model):
    u, v = calm_model.get_wind_components(lat=0.0, lon=0.0, altitude_m=1000.0)
    assert u == pytest.approx(0.0)
    assert v == pytest.approx(0.0)


def test_headwind_and_groundspeed_are_zero_in_calm_air(calm_model):
    result = calm_model.calculate_headwind_and_groundspeed(
        lat=0.0, lon=0.0, altitude_m=1000.0, heading_rad=0.0, tas_m_s=200.0
    )
    assert result["headwind_m_s"] == pytest.approx(0.0)
    assert result["crosswind_m_s"] == pytest.approx(0.0)
    assert result["groundspeed_m_s"] == pytest.approx(200.0)


def test_flying_with_the_wind_is_a_tailwind(uniform_easterly_model):
    # u=+20 is an eastward-blowing wind; heading due east (90 deg) runs with it.
    result = uniform_easterly_model.calculate_headwind_and_groundspeed(
        lat=0.0, lon=0.0, altitude_m=1000.0, heading_rad=math.radians(90), tas_m_s=200.0
    )
    assert result["headwind_m_s"] == pytest.approx(-20.0, abs=1e-6)
    assert result["groundspeed_m_s"] == pytest.approx(220.0, abs=1e-6)


def test_flying_against_the_wind_is_a_headwind(uniform_easterly_model):
    # Heading due west (270 deg) runs directly into the eastward-blowing wind.
    result = uniform_easterly_model.calculate_headwind_and_groundspeed(
        lat=0.0, lon=0.0, altitude_m=1000.0, heading_rad=math.radians(270), tas_m_s=200.0
    )
    assert result["headwind_m_s"] == pytest.approx(20.0, abs=1e-6)
    assert result["groundspeed_m_s"] == pytest.approx(180.0, abs=1e-6)


def test_groundspeed_never_goes_negative(uniform_easterly_model):
    result = uniform_easterly_model.calculate_headwind_and_groundspeed(
        lat=0.0, lon=0.0, altitude_m=1000.0, heading_rad=math.radians(90), tas_m_s=5.0
    )
    assert result["groundspeed_m_s"] >= 0.0
