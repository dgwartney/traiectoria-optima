SELECT name, iso_country, iso_region, iata_code, latitude_deg, longitude_deg, type
FROM airports_our_airports
WHERE (type = "large_airport" or type = "medium_airport" ) and iso_country = "US";

DROP TABLE IF EXISTS us_large_airports;

CREATE TABLE us_large_airports AS 
SELECT name, iso_country, iso_region, iata_code, latitude_deg, longitude_deg, type
FROM airports_our_airports
WHERE type = "large_airport" and iso_country = "US";



DROP TABLE IF EXISTS united_airlines_routes;

CREATE TABLE united_airlines_routes AS
SELECT airline_code,source_airport_code, destination_airport_code, codeshare,stops,equipment
FROM routes_open_flights
WHERE airline_code = 'UA'
AND ( source_airport_code IN (SELECT iata_code FROM us_large_airports) OR
destination_airport_code IN (SELECT iata_code FROM us_large_airports));

DROP TABLE IF EXISTS united_airlines_airports;

CREATE TABLE united_airlines_airports AS
SELECT name, iso_country, iso_region, iata_code, latitude_deg, longitude_deg, type
FROM us_large_airports
WHERE
    iata_code IN (SELECT DISTINCT source_airport_code FROM united_airlines_routes) OR
    iata_code IN (SELECT DISTINCT destination_airport_code FROM united_airlines_routes)
GROUP BY name, iso_country, iso_region, iata_code, latitude_deg, longitude_deg, type;

DROP TABLE IF EXISTS united_airlines_dist_routes;

CREATE TABLE united_airlines_dist_routes AS
SELECT airline_code,source_airport_code, destination_airport_code, codeshare,stops,equipment,
    round(2 * 6371 * asin(
    sqrt(
      pow(sin(radians(src.latitude_deg - src.latitude_deg) / 2), 2) +
      cos(radians(src.latitude_deg)) * cos(radians(dest.latitude_deg)) *
      pow(sin(radians(dest.longitude_deg - src.longitude_deg) / 2), 2)
    ))) AS distance_km
FROM united_airlines_routes AS routes
INNER JOIN united_airlines_airports AS src
    ON routes.source_airport_code = src.iata_code
INNER JOIN united_airlines_airports AS dest
    ON routes.destination_airport_code = dest.iata_code;

-- Start spooling to a file
.output data/processed/airports.csv

-- Optional: format nicely (table, csv, line, etc.)
.headers on
.mode column

-- Run queries (output goes into the file)
SELECT name, iso_country, iso_region, iata_code, latitude_deg, longitude_deg, type
FROM united_airlines_airports;
-- Stop spooling and return output to the console/terminal
.output stdout

.output data/processed/routes.csv

.headers on

.mode column

SELECT airline_code,source_airport_code, destination_airport_code, codeshare,stops,equipment, distance_km
FROM united_airlines_dist_routes;

.output stdout
