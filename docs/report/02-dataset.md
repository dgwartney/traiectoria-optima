## 2. Dataset
- Data sources (OpenFlights airports/routes, OurAirports)
- Scope: the world airline network — 3,387 airports and 66,332 routes after
  cleaning. One experiment (`shortest-vs-fewest`) works on a 94-airport US
  large-airport slice of it, frozen as its own snapshot; the evaluation in §7
  uses the whole network, because the queries it asks are long-haul
- Cleaning and preparation steps
- Basic dataset statistics (airport count, route count, degree distribution, disconnected airports)
