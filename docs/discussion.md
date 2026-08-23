# Flight Route Optimization

This document is a


## Factors for flight route selection

- Airfare Cost
- Time of Travel
- Airline preference
- Deparature and Arrival Airports**


** Some passengers have no alternative but to use secondary transportation to get to their destination airport. Also
if you are going abroad not all airlines provide service to every country. This most relevant on the African and
Asian continents.

## Least Path Perspectives

To aid with further discussion we

## Flight Route

_Flight Route_ is the selection of points (airports) from a departure airport, the starting point,
to an arrival airport, the destination. This is a two-dimensional problem that can use the position one or more
airports need to reach the arrival aiport. Position of each airport is specified by their respective
_latitude_ and _longitude_. This is the mind set the everyone uses to plan a flight to their
favorite destination for that get away carribean vacation, family visit, or business trip. You visit
any one of the available internet flight travel sites such as Google Flights, KAYAK, Expedia, and others.

Typical decision points include preferred airlines (to use bonus miles or upgrades), non-stop versus a connecting flight
(with associated layover time)


A _flight route_ is the planned path on a map, a _flight path_ is the actual 3D trajectory flown over time,
and _flight dynamics_ is the physical rotation and movement of the aircraft around its center of gravity.

## Mathematical Perspectives

Flight Route:

Modeled as a 2D or 3D geometric curve defined by a sequence of discrete waypoints $(x_i, y_i, z_i)$.
Uses [geodesics](https://en.wikipedia.org/wiki/Geodesic), [great-circle distance formulas](https://en.wikipedia.org/wiki/Great-circle_distance),
or piecewise linear/polynomial segments on a [cartographic projection](https://en.wikipedia.org/wiki/Map_projection).


## Flight Path

Modeled as a continuous time-parameterized trajectory vector $\mathbf{r}(t) = [x(t), y(t), z(t)]^\top$ in a global coordinate system.Derived from kinematic equations integrating velocity vectors and acceleration over time.


## Flight Dynamics:

Modeled by a set of non-linear differential equations (such as rigid-body Newton-Euler equations) governing translational and rotational states.Uses state vectors for position, velocity, and Euler angles or quaternions $[\phi, \theta, \psi]^\top$, driven by forces and moments acting on the body axis.Least Path Perspectives


## Flight Route

Optimizes path length or fuel cost using global graph search algorithms (like \(A^{*}\) or Dijkstra) across air traffic waypoints.Subject to static constraints like airspace boundaries, terrain avoidance, and jet stream optimization.

## Flight Path

Optimizes the trajectory dynamically using calculus of variations or optimal control theory (like Pontryagin's Minimum Principle).

Minimizes a performance index like total energy expenditure or time-of-flight under wind and aircraft performance constraints.Flight Dynamics:Optimizes the control path (elevator, aileron, rudder deflections) to transition between states with minimal control energy or actuator wear.Solves for the path of least resistance through aerodynamic and inertial force fields moment-by-moment.Would you like me to explain the differential equations used in flight dynamics or explore optimal control theory for flight paths in more detail?


## Cost from the different perspectives

- Passengers

- Pilots

- Airlines




## Flight Type Comparison


**Non-stop flight:** Goes straight from start to finish with no stops.

**Connecting flight:** Requires a change of planes and a layover at a stop.

**Direct flight:** Makes a stop, but keeps the same flight number and often the same plane.
(Note: A direct flight is not the opposite of a non-stop flight).

## References
[Non-Stop Flight: Rules & Limits - Navan](https://www.indianeagle.com/traveldiary/difference-between-a-direct-flight-and-nonstop-flight/)

[Direct vs. Non-Stop Flights: What’s the Difference? | AirHelp](https://www.airhelp.com/en/blog/direct-vs-non-stop-flight/)



## Flight Delays



## Air Carrier Industry Scheduled Service Traffic Stats (Blue Book)

https://www.bts.gov/browse-statistical-products-and-data/bts-publications/air-carrier-industry-scheduled-service-traffic
https://www.transtats.bts.gov/ot_delay/OT_DelayCause1.asp?20=E


## On time arrival data:


https://www.opendatanetwork.com/dataset/data.bts.gov/56fa-sf82


Percentage of flights arriving on-time. A flight is on-time if it arrives within 15 minutes of the schedule arrival time. Data are available for those carriers that had at least 1% of domestic enplanements in the previous year. The last 25 months of data include only carriers that reported in each of the last 25 months to retain comparability. Earlier data includes all reporting carriers. A scheduled operation consists of any nonstop segment of a flight.  The Bureau of Transportation Statistics air collects performance data from U.S. air carriers and international carriers operating within the U.S.
