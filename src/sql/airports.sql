SELECT name, iso_country, iso_region, iata_code, latitude_deg, longitude_deg
FROM airports_our_airports
WHERE (type = "large_airport" or type = "medium_airport" ) and iso_country = "US";
