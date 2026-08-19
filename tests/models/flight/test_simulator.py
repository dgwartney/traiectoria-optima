import pytest

from aircraft import CommercialAircraft
from simulator import GateToGateFlightSimulator


@pytest.fixture
def aircraft():
    return CommercialAircraft.get_preset("A321neo")


def test_simulate_returns_expected_keys(aircraft):
    sim = GateToGateFlightSimulator(aircraft, distance_nmi=1500, headwind_kts=0)
    result = sim.simulate()

    expected_keys = {
        "aircraft_model",
        "flight_distance_nmi",
        "airborne_time_hr",
        "gate_to_gate_time_hr",
        "gate_to_gate_time_formatted",
        "total_fuel_burned_kg",
        "average_groundspeed_kts",
    }
    assert expected_keys == set(result.keys())


def test_simulate_reports_the_requested_aircraft_and_distance(aircraft):
    sim = GateToGateFlightSimulator(aircraft, distance_nmi=1500, headwind_kts=0)
    result = sim.simulate()

    assert result["aircraft_model"] == "A321neo"
    assert result["flight_distance_nmi"] == pytest.approx(1500, abs=1.0)


def test_simulate_produces_positive_time_and_fuel(aircraft):
    sim = GateToGateFlightSimulator(aircraft, distance_nmi=1500, headwind_kts=0)
    result = sim.simulate()

    assert result["airborne_time_hr"] > 0
    assert result["gate_to_gate_time_hr"] > result["airborne_time_hr"]
    assert result["total_fuel_burned_kg"] > 0
    assert result["average_groundspeed_kts"] > 0


def test_headwind_increases_gate_to_gate_time_versus_no_wind(aircraft):
    no_wind = GateToGateFlightSimulator(aircraft, distance_nmi=1500, headwind_kts=0).simulate()
    headwind = GateToGateFlightSimulator(aircraft, distance_nmi=1500, headwind_kts=40).simulate()

    assert headwind["gate_to_gate_time_hr"] > no_wind["gate_to_gate_time_hr"]


def test_heavier_payload_burns_more_fuel(aircraft):
    light = GateToGateFlightSimulator(
        aircraft, distance_nmi=1500, headwind_kts=0, payload_kg=5000
    ).simulate()
    heavy = GateToGateFlightSimulator(
        aircraft, distance_nmi=1500, headwind_kts=0, payload_kg=20000
    ).simulate()

    assert heavy["total_fuel_burned_kg"] > light["total_fuel_burned_kg"]
