from simulator import GateToGateFlightSimulator
from aircraft import CommercialAircraft

if __name__ == '__main__':

    aircraft = CommercialAircraft.get_preset('737-800')
    simulator = GateToGateFlightSimulator(aircraft, "1200")
    print(simulator.simulate())

