from simulator import GateToGateFlightSimulator
from aircraft import CommercialAircraft

if __name__ == '__main__':
    # Instantiate an Airbus A321neo preset model
    aircraft = CommercialAircraft.get_preset("A321neo")

    # Run simulation: 3,000 nmi with a 20-knot headwind component
    sim = GateToGateFlightSimulator(aircraft, distance_nmi=3000, headwind_kts=20)
    results = sim.simulate(cruise_alt_ft=35000, cruise_mach=0.78)

    for key, value in results.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

