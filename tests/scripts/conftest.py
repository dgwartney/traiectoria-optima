"""A miniature processed dataset for the snapshot and experiment scripts.

Small enough that every count in the tests can be checked by eye, but in the
real processed schema -- the scripts slice those files verbatim, so the column
set is part of what is under test.
"""

import pytest

AIRPORTS_CSV = """\
name,iso_country,iso_region,continent,municipality,iata_code,icao_code,latitude_deg,longitude_deg,elevation_ft,scheduled_service,type,is_international,wikipedia_link
San Francisco International Airport,US,US-CA,NA,San Francisco,SFO,KSFO,37.619806,-122.374821,13.0,yes,large_airport,yes,https://en.wikipedia.org/wiki/SFO
Boston Logan International Airport,US,US-MA,NA,Boston,BOS,KBOS,42.36197,-71.0079,20.0,yes,large_airport,yes,https://en.wikipedia.org/wiki/BOS
Portland International Jetport,US,US-ME,NA,Portland,PWM,KPWM,43.646198,-70.309303,76.0,yes,medium_airport,no,https://en.wikipedia.org/wiki/PWM
Vancouver International Airport,CA,CA-BC,NA,Vancouver,YVR,CYVR,49.193901,-123.183998,4.0,yes,large_airport,yes,https://en.wikipedia.org/wiki/YVR
"""

ROUTES_CSV = """\
flight_number,airline_code,source_airport_code,destination_airport_code,codeshare,stops,equipment,distance_km
UA0001,UA,SFO,BOS,,0,320,4341.022084519025
UA0002,UA,BOS,SFO,,0,320,4341.022084519025
UA0003,UA,BOS,PWM,,0,CR7,152.5
UA0004,UA,SFO,YVR,,0,738,1287.3
AA0001,AA,SFO,BOS,Y,0,321,4341.022084519025
"""


@pytest.fixture
def processed(tmp_path):
    """Write the miniature dataset and return its directory."""
    directory = tmp_path / "processed"
    directory.mkdir()
    (directory / "airports.csv").write_text(AIRPORTS_CSV)
    (directory / "routes.csv").write_text(ROUTES_CSV)
    return directory


@pytest.fixture
def snapshot_args(processed, tmp_path):
    """Return the path arguments pointing the script at the miniature data."""
    return [
        "--airports-csv", str(processed / "airports.csv"),
        "--routes-csv", str(processed / "routes.csv"),
        "--root", str(tmp_path / "snapshots"),
    ]
