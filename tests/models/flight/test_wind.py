import math

import numpy as np
import pytest

from wind import AtmosphericWindModel, _RegularGrid


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


class TestTheGridInterpolator:
    """`_RegularGrid`, which replaced `scipy.interpolate.RegularGridInterpolator`.

    Removing scipy meant writing the interpolation, so these pin the three
    behaviours that were easy to get wrong. Equivalence with scipy was
    verified over 8,080 points across 40 random grids before the dependency
    was dropped; these tests are what keeps the behaviour once the reference
    implementation is no longer installed to compare against.
    """

    @pytest.fixture
    def ramp(self):
        """A grid whose value equals its longitude index, on uneven axes."""
        alts = np.array([0.0, 1000.0])
        lats = np.array([0.0, 10.0])
        lons = np.array([0.0, 1.0, 100.0])  # deliberately not evenly spaced
        values = np.zeros((2, 2, 3))
        values[:, :, 0] = 0.0
        values[:, :, 1] = 1.0
        values[:, :, 2] = 2.0
        return _RegularGrid((alts, lats, lons), values, fill_value=0.0)

    def test_it_reproduces_grid_points_exactly(self, ramp):
        assert ramp((0.0, 0.0, 0.0)) == pytest.approx(0.0)
        assert ramp((0.0, 0.0, 1.0)) == pytest.approx(1.0)
        assert ramp((1000.0, 10.0, 100.0)) == pytest.approx(2.0)

    def test_it_interpolates_on_unevenly_spaced_axes(self, ramp):
        """Halfway between lon 1.0 and 100.0 is halfway between 1.0 and 2.0.

        An implementation that divided by a uniform step instead of finding
        the bracketing interval would get this wrong.
        """
        assert ramp((0.0, 0.0, 50.5)) == pytest.approx(1.5)

    def test_the_upper_boundary_is_inside_the_grid(self, ramp):
        """searchsorted returns len(axis) here; the index has to be clamped."""
        assert ramp((1000.0, 0.0, 100.0)) == pytest.approx(2.0)

    @pytest.mark.parametrize(
        "point",
        [
            (-1.0, 0.0, 0.0),
            (2000.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            (0.0, 0.0, 101.0),
        ],
        ids=["below-alt", "above-alt", "below-lat", "above-lon"],
    )
    def test_a_point_outside_any_axis_returns_the_fill_value(self, ramp, point):
        """Not clamped onto the nearest face -- the whole point is filled."""
        assert ramp(point) == 0.0

    def test_an_axis_needs_at_least_two_points(self):
        with pytest.raises(ValueError, match="at least two"):
            _RegularGrid((np.array([0.0]), np.array([0.0, 1.0])), np.zeros((1, 2)))

    def test_values_must_match_the_axis_lengths(self):
        with pytest.raises(ValueError, match="expected"):
            _RegularGrid((np.array([0.0, 1.0]), np.array([0.0, 1.0])), np.zeros((2, 3)))
