"""Gate-to-gate flight time and fuel-burn simulator."""

import math
from atomosphere import InternationalStandardAtmosphere
from aircraft import CommercialAircraft

class GateToGateFlightSimulator:
    """Integrates a climb/cruise/descent trajectory for a single flight."""

    def __init__(self, aircraft: CommercialAircraft, distance_nmi: float, headwind_kts: float =0.0, payload_kg: float = 18000):
        """Set up the flight's initial conditions.

        Args:
            aircraft: Aircraft performance model to fly.
            distance_nmi: Great-circle route distance (nautical miles).
            headwind_kts: Constant headwind component along the route (knots).
            payload_kg: Payload mass carried for the flight (kg).
        """
        self.ac: CommercialAircraft = aircraft
        self.distance_m: float = float(distance_nmi) * 1852.0  # Nautical miles to meters
        self.headwind_m_s: float  = float(headwind_kts) * 0.514444 # Knots to m/s
        
        # Weight setup
        self.current_mass: float  = self.ac.oew + payload_kg + (self.ac.max_fuel * 0.6)
        
    def simulate(self, cruise_alt_ft=35000, cruise_mach=0.78):
        """Simulate the full climb/cruise/descent trajectory.

        Args:
            cruise_alt_ft: Target cruise altitude (feet).
            cruise_mach: Target cruise Mach number.

        Returns:
            A dict summarizing the flight: ``aircraft_model``,
            ``flight_distance_nmi``, ``airborne_time_hr``,
            ``gate_to_gate_time_hr``, ``gate_to_gate_time_formatted``,
            ``total_fuel_burned_kg``, and ``average_groundspeed_kts``.
        """
        cruise_alt_m = cruise_alt_ft * 0.3048
        
        # Ground taxi times (fixed operational baseline)
        taxi_out_min = 15.0
        taxi_in_min = 10.0
        taxi_fuel_kg = 250.0  # Taxi fuel estimate

        self.current_mass -= taxi_fuel_kg
        
        dt = 2.0  # Integration step in seconds
        time = 0.0
        dist_covered = 0.0
        fuel_consumed = taxi_fuel_kg

        altitude = 0.0
        
        # PHASE 1: CLIMB PHASE
        while altitude < cruise_alt_m and dist_covered < (self.distance_m * 0.5):
            temp, press, rho, a = InternationalStandardAtmosphere.get_properties(altitude)
            target_tas = min(cruise_mach * a, 250 * 0.514444 if altitude < 3048 else cruise_mach * a) # 250 kts below 10,000ft constraint
            
            # 5-degree climb profile approximation
            gamma = math.radians(4.0)
            forces = self.ac.calculate_forces(self.current_mass, altitude, target_tas, climb_angle_rad=gamma)
            
            thrust_req = forces["drag"] + self.current_mass * InternationalStandardAtmosphere.G0 * math.sin(gamma)
            thrust = min(thrust_req, forces["max_thrust"])
            
            fuel_flow = thrust * forces["tsfc"] # kg/s
            
            groundspeed = target_tas * math.cos(gamma) - self.headwind_m_s
            
            altitude += target_tas * math.sin(gamma) * dt
            dist_covered += groundspeed * dt
            time += dt
            fuel_step = fuel_flow * dt
            fuel_consumed += fuel_step
            self.current_mass -= fuel_step

        climb_time_min = time / 60.0
        climb_dist_nmi = dist_covered / 1852.0

        # PHASE 3: DESCENT PHASE ESTIMATION (3-degree glide slope back-calculation)
        descent_dist_m = cruise_alt_m / math.tan(math.radians(3.0))
        cruise_target_dist = self.distance_m - descent_dist_m

        # PHASE 2: CRUISE PHASE
        cruise_start_time = time
        while dist_covered < cruise_target_dist:
            temp, press, rho, a = InternationalStandardAtmosphere.get_properties(cruise_alt_m)
            tas = cruise_mach * a
            forces = self.ac.calculate_forces(self.current_mass, cruise_alt_m, tas, climb_angle_rad=0.0)
            
            thrust = forces["drag"]  # Equilibrium T = D
            fuel_flow = thrust * forces["tsfc"]
            
            groundspeed = tas - self.headwind_m_s
            
            dist_covered += groundspeed * dt
            time += dt
            fuel_step = fuel_flow * dt
            fuel_consumed += fuel_step
            self.current_mass -= fuel_step

        cruise_time_min = (time - cruise_start_time * 60) / 60.0

        # PHASE 3: DESCENT INTEGRATION
        descent_start_time = time
        while altitude > 0 and dist_covered < self.distance_m:
            gamma = math.radians(-3.0)
            temp, press, rho, a = InternationalStandardAtmosphere.get_properties(altitude)
            tas = cruise_mach * a * 0.85 # Slowdown on descent
            
            forces = self.ac.calculate_forces(self.current_mass, altitude, tas, climb_angle_rad=gamma)
            
            # Idle thrust modeling during descent (10% max thrust)
            thrust = 0.10 * forces["max_thrust"]
            fuel_flow = thrust * forces["tsfc"]
            
            groundspeed = tas * math.cos(gamma) - self.headwind_m_s
            
            altitude = max(0.0, altitude + tas * math.sin(gamma) * dt)
            dist_covered += groundspeed * dt
            time += dt
            fuel_step = fuel_flow * dt
            fuel_consumed += fuel_step
            self.current_mass -= fuel_step

        flight_time_min = time / 60.0
        gate_to_gate_time_min = flight_time_min + taxi_out_min + taxi_in_min
        fuel_consumed += 150.0 # Add taxi in fuel

        return {
            "aircraft_model": self.ac.model_name,
            "flight_distance_nmi": round(self.distance_m / 1852.0, 1),
            "airborne_time_hr": round(flight_time_min / 60.0, 2),
            "gate_to_gate_time_hr": round(gate_to_gate_time_min / 60.0, 2),
            "gate_to_gate_time_formatted": f"{int(gate_to_gate_time_min // 60)}h {int(gate_to_gate_time_min % 60)}m",
            "total_fuel_burned_kg": round(fuel_consumed, 1),
            "average_groundspeed_kts": round((self.distance_m / 1852.0) / (flight_time_min / 60.0), 1)
        }
