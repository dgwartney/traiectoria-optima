--
-- Exploratory derivation of the United Airlines subset.
--
-- This no longer builds data/processed/*.csv. `src/data/flight_network.py`
-- does that with pandas, reusing the tested `flight_planner.geo.Haversine`
-- rather than a second copy of the formula. What remains here is the subset
-- derivation, kept as tables for ad-hoc SQL exploration.
--
-- It now reads the processed `airports` and `routes` tables rather than the
-- raw ones, so `distance_km` arrives precomputed and the enriched airport
-- columns are available. Run with:
--
--     make united_airlines_tables
--

DROP TABLE IF EXISTS us_large_airports;

CREATE TABLE us_large_airports AS
SELECT *
FROM airports
WHERE type = 'large_airport' AND iso_country = 'US';

DROP TABLE IF EXISTS united_airlines_routes;

-- Historical note: this filter used to read
--     source_airport_code IN (...) OR destination_airport_code IN (...)
-- against the raw tables, but the distance join below INNER JOINed *both*
-- endpoints against a US-large-only airports table -- silently tightening the
-- OR into an AND. The stated OR admitted 1,996 routes; the join yielded 861.
-- The AND is written explicitly here, because 861 is what was published.
CREATE TABLE united_airlines_routes AS
SELECT *
FROM routes
WHERE airline_code = 'UA'
  AND source_airport_code IN (SELECT iata_code FROM us_large_airports)
  AND destination_airport_code IN (SELECT iata_code FROM us_large_airports);

DROP TABLE IF EXISTS united_airlines_airports;

CREATE TABLE united_airlines_airports AS
SELECT *
FROM us_large_airports
WHERE iata_code IN (SELECT source_airport_code FROM united_airlines_routes)
   OR iata_code IN (SELECT destination_airport_code FROM united_airlines_routes);

SELECT
    (SELECT COUNT(*) FROM united_airlines_airports) AS airports,
    (SELECT COUNT(*) FROM united_airlines_routes)   AS routes;
