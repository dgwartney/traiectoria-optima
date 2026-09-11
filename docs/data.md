# OpenFlights Data Schemas

This document details the data schemas for the OpenFlights route and airport datasets, including column positions, field names, data types, nullability rules, and descriptive notes.

---

## 1. Routes Dataset Schema (`routes.dat`)

The routes dataset describes individual airline routes connecting origin and destination airports.

### Column Specification

| Column # | Field Name | Data Type | Nullable / Missing | Description | Example |
| :---: | :--- | :--- | :---: | :--- | :--- |
| **1** | `airline` | `VARCHAR(3)` | No | 2-letter IATA or 3-letter ICAO airline code. | `2B` |
| **2** | `airline_id` | `INTEGER` | Yes (`\N`) | Unique OpenFlights database identifier for the airline. | `410` |
| **3** | `source_airport` | `VARCHAR(4)` | No | 3-letter IATA or 4-letter ICAO code of the departure airport. | `AER` |
| **4** | `source_airport_id` | `INTEGER` | Yes (`\N`) | Unique OpenFlights database identifier for the source airport. | `2965` |
| **5** | `destination_airport` | `VARCHAR(4)` | No | 3-letter IATA or 4-letter ICAO code of the arrival airport. | `KZN` |
| **6** | `destination_airport_id` | `INTEGER` | Yes (`\N`) | Unique OpenFlights database identifier for the destination airport. | `2990` |
| **7** | `codeshare` | `CHAR(1)` | Yes (empty) | `Y` if the flight is operated as a codeshare; empty if operated directly. | `""` |
| **8** | `stops` | `INTEGER` | No | Number of intermediate stops (`0` = non-stop/direct). | `0` |
| **9** | `equipment` | `VARCHAR(50)` | Yes (empty) | 3-letter IATA equipment/aircraft codes, separated by spaces if multiple. | `CR2` |

### Sample Data

```csv
2B,410,AER,2965,KZN,2990,,0,CR2
2B,410,ASF,2966,KZN,2990,,0,CR2
2B,410,ASF,2966,MRV,2962,,0,CR2
2B,410,CEK,2968,KZN,2990,,0,CR2
2B,410,CEK,2968,OVB,4078,,0,CR2
2B,410,DME,4029,KZN,2990,,0,CR2
2B,410,DME,4029,NBC,6969,,0,CR2
```

---

## 2. Airports Dataset Schema (`airports.dat` / `airports-extended.dat`)

The airports dataset contains geographic, navigational, and administrative details for global airports, train stations, and ferry terminals.

### Column Specification

| Column # | Field Name | Data Type | Nullable / Missing | Description | Example |
| :---: | :--- | :--- | :---: | :--- | :--- |
| **1** | `airport_id` | `INTEGER` | No | Unique OpenFlights database identifier for this facility. | `1` |
| **2** | `name` | `VARCHAR(100)` | No | Name of the airport / facility (quoted string). | `"Goroka Airport"` |
| **3** | `city` | `VARCHAR(100)` | Yes (`\N`) | Main city served by the airport (quoted string). | `"Goroka"` |
| **4** | `country` | `VARCHAR(100)` | No | Country or territory where the airport is located (quoted string). | `"Papua New Guinea"` |
| **5** | `iata` | `VARCHAR(3)` | Yes (`\N`) | 3-letter IATA identifier. | `"GKA"` |
| **6** | `icao` | `VARCHAR(4)` | Yes (`\N`) | 4-letter ICAO identifier. | `"AYGA"` |
| **7** | `latitude` | `DECIMAL(10, 6)` | No | Latitude in decimal degrees (North is positive, South is negative). | `-6.081689834590001` |
| **8** | `longitude` | `DECIMAL(10, 6)` | No | Longitude in decimal degrees (East is positive, West is negative). | `145.391998291` |
| **9** | `altitude` | `INTEGER` | No | Elevation above mean sea level in feet. | `5282` |
| **10** | `timezone_offset`| `DECIMAL(4, 2)` | Yes (`\N`) | Hours offset from UTC (standard daylight adjustment not included). | `10` |
| **11** | `dst` | `CHAR(1)` | Yes (`\N`) | Daylight saving time rule (see table below). | `"U"` |
| **12** | `tz_database` | `VARCHAR(50)` | Yes (`\N`) | Olson / IANA timezone identifier (quoted string). | `"Pacific/Port_Moresby"` |
| **13** | `type` | `VARCHAR(20)` | No | Facility category: `airport`, `station`, `port`, or `unknown`. | `"airport"` |
| **14** | `source` | `VARCHAR(50)` | No | Data origin source (e.g., `OurAirports`, `Legacy`, `User`). | `"OurAirports"` |

### Daylight Saving Time (`dst`) Reference Values

| Code | Region / Regime |
| :---: | :--- |
| `E` | Europe |
| `A` | US / Canada |
| `S` | South America |
| `O` | Australia |
| `Z` | New Zealand |
| `N` | None (does not observe DST) |
| `U` | Unknown |

### Sample Data

```csv
1,"Goroka Airport","Goroka","Papua New Guinea","GKA","AYGA",-6.081689834590001,145.391998291,5282,10,"U","Pacific/Port_Moresby","airport","OurAirports"
2,"Madang Airport","Madang","Papua New Guinea","MAG","AYMD",-5.20707988739,145.789001465,20,10,"U","Pacific/Port_Moresby","airport","OurAirports"
3,"Mount Hagen Kagamuga Airport","Mount Hagen","Papua New Guinea","HGU","AYMH",-5.826789855957031,144.29600524902344,5388,10,"U","Pacific/Port_Moresby","airport","OurAirports"
4,"Nadzab Airport","Nadzab","Papua New Guinea","LAE","AYNZ",-6.569803,146.725977,239,10,"U","Pacific/Port_Moresby","airport","OurAirports"
5,"Port Moresby Jacksons International Airport","Port Moresby","Papua New Guinea","POM","AYPY",-9.443380355834961,147.22000122070312,146,10,"U","Pacific/Port_Moresby","airport","OurAirports"
```




## Free Airport Coordinates APIs (IATA to Lat/Long)

> **Historical.** The pipeline no longer calls any of these. Coordinates now
> come from `data/raw/our_airports/airports.csv`, which the project already
> vendors — see [International Airports Scrape](#4-international-airports-scrape-airports_rawjson)
> below. AirportsAPI.com turned out to be serving OurAirports data back over the
> network: 1,477 of 1,483 coordinate pairs were bit-identical, and of the three
> that differed by more than 0.05°, the API was wrong in all three. Resolving
> locally is faster, reproducible, needs no rate limiting, and fixes those rows.
> This survey is kept for reference.

A curated list of free, online APIs to quickly resolve IATA airport codes into latitude and longitude coordinates.

### 1. AirportsAPI.com (Easiest / No Auth)
This is the most straightforward option because it requires **no API keys, no sign-ups, and no authentication**. You can start making requests directly in your browser or code immediately.

**Endpoint Example:** [https://airportsapi.com](https://airportsapi.com)

### Sample JSON Response```json
{
  "name": "London Heathrow Airport",
  "code": "EGLL",
  "iata_code": "LHR",
  "latitude": 51.4706,
  "longitude": -0.461941,
  "type": "large_airport"
}

### 2. AirLabs Airport Database API (Best for Production-Ready Free Tier)
AirLabs offers a robust, developer-friendly API. Their **Free Tier** includes full access to global IATA/ICAO codes alongside coordinates, though it requires a quick sign-up to get an API key.

**Endpoint Example:** [AirLabs Airports Docs](https://airlabs.co)

### Key Returned Parameters*   `iata_code`
*   `icao_code`
*   `lat`
*   `lng`

### 3. API Ninjas - Airports API (Great for General Projects)
API Ninjas provides a comprehensive airport lookup tool. Their free tier covers thousands of requests per month with a standard free account API key.

**Documentation:** [API Ninjas Airports](https://api-ninjas.com) *(Requires `X-Api-Key` header)*

### Alternative: Downloadable Datasets
If you don't want to make live API calls over the internet and prefer a local database,
you can download **[The Global Airport Database](https://partow.net)** for free.
It maps IATA codes to Lat/Long positions in a simple token-delimited text format.

## 4. International Airports Scrape (`airports_raw.json`)

`src/data/generate_airports_raw.py` regenerates `airports_raw.json`, the raw
input consumed by `src/data/international_airports.py`, which joins it against
the vendored OurAirports data to build
`data/processed/international_airports.csv`. It uses Playwright to load
[List of international airports by
country](https://en.wikipedia.org/wiki/List_of_international_airports_by_country)
and extract `{region, country, location, airport, href}` for every airport
link on the page.

### Coordinates and IATA code overrides

`src/data/international_airports.py` attaches coordinates to each scraped
airport by joining on the IATA code against
`data/raw/our_airports/airports.csv`. It makes no network requests.

```bash
make international_airports
```

Ten of the 1,492 scraped codes do not join, because Wikipedia and OurAirports
disagree about the code or because neither source assigns one. Each was checked
against IATA's official registry at
<https://www.iata.org/en/publications/directories/code-search/>, which resolves
every case: four Wikipedia codes are stale, two are valid codes OurAirports has
retired alongside a closed field, two describe an airport carrying three codes
(one of them a metropolitan-area code rather than an airport code), and two are
codes no registry recognises.

| Wiki code | Airport | IATA registry | OurAirports | What happened |
|---|---|---|---|---|
| `CSL` | Cabo San Lucas Intl | not found; `CSW` = Cabo San Lucas Internacional | `MMSL`, IATA `CSW` | Wikipedia code is stale |
| `FRU` | Manas Intl, Bishkek | not found; `BSZ` = Bishkek, Manas Intl | `UAFM`, IATA `BSZ` | Wikipedia code is stale |
| `KVD` | Ganja Intl | not found; `GNJ` = Ganja Airport | `UBBG`, IATA `GNJ` | Wikipedia code is stale |
| `REP` | Siem Reap Intl | not found; `SAI` = Siem Reap Angkor | `VDSA`, IATA `SAI` | Airport replaced; old field closed |
| `TIP` | Tripoli Intl | **valid** — Tripoli Intl. | `LY-0019`, closed, no IATA | OurAirports retired the code |
| `NLV` | Mykolaiv Intl | **valid** — Mykolaiv Intl. | `UKON`, closed, no IATA | OurAirports retired the code |
| `MLH` | EuroAirport Basel–Mulhouse–Freiburg | **valid** — EuroAirport French | `LFSB`, IATA `BSL` | One airport, three codes |
| `EAP` | EuroAirport Basel–Mulhouse–Freiburg | **valid** — Basel/Mulhouse Metropolitan Area | none | Metro code, not an airport code |
| `HZO` | Ho Airport | not found | `DGAH`, no IATA | Neither source has a code |
| `QGY` | Győr-Pér Intl | not found | `LHPR`, no IATA | Neither source has a code |

The mapping lives in `data/reference/iata_code_overrides.csv`, keyed on the
scraped code and pointing at an OurAirports `ident` — `ident` rather than IATA
code, because that is the stable identifier and the IATA code is exactly what is
in dispute. With the overrides applied, all 1,492 airports resolve.

A stale override is a hard error, not a silent skip: the script exits non-zero
if an `ident` is unknown or if an override's code no longer appears in the
scrape.

Because the `iata_registry` column asserts something about a live external
source, it has a shelf life. Re-check it:

```bash
make verify_iata_codes
```

That drives the IATA search page with Playwright, one lookup per override, and
exits non-zero if any verdict has changed.

#### The `canonical_iata` column

The override table's `canonical_iata` column rewrites the code that appears in
the output. It is populated for exactly one row:

| Scraped | Emitted | Why |
|---|---|---|
| `EAP` | `BSL` | `EAP` is a metropolitan-area code and identifies no airport; `BSL` is the code OurAirports and IATA both use for the field itself. |

Wikipedia lists EuroAirport three times — Basel/`EAP`, Mulhouse/`BSL`,
Freiburg/`MLH` — and the Basel row's `EAP` is the only scraped code that names
no airport. That substitution used to be a hand-edit applied to the generated
CSV after each build, which meant a rebuild silently discarded it. Declaring it
here makes it reproducible: regenerating now yields the committed `iata` column
byte for byte.

The column is deliberately empty for every other row. The four stale codes
(`CSL`, `FRU`, `KVD`, `REP`) are **not** rewritten — the overrides fix their
coordinates, while the `iata` column continues to report what the source
actually said. Rewriting those too would change the column's meaning from "what
Wikipedia says" to "what IATA says", which is a larger decision than this table
should make on its own.

### Requirements — local (`uv`) environment

```bash
uv sync                                    # installs the playwright package
uv run playwright install --with-deps chromium
uv run python src/data/generate_airports_raw.py data/raw/wikipedia/airports_raw.json
```

### Requirements — Google Colab

Colab notebooks need extra setup that a local `uv`-managed environment
already has, and the script's async API is deliberately used so it can be
awaited directly from a cell:

1. **Install the package and browser** in a setup cell — Colab's base image
   ships neither:
   ```python
   !pip install playwright
   !playwright install --with-deps chromium
   ```
   `--with-deps` is required, not optional — it apt-installs the shared
   libraries Chromium needs that Colab's minimal container lacks. Skipping it
   causes the browser launch to fail with missing `.so` errors.
2. **Headless only** — Colab has no display, so the script's default
   `launch(headless=True)` is required (already the case; do not pass
   `headless=False`).
3. **Use the async API, not `asyncio.run()`** — Colab's kernel already runs
   an event loop, so Playwright's sync API (`sync_playwright`) raises
   `Error: It looks like you are using Playwright Sync API inside the
   asyncio loop` if called from a cell, and `asyncio.run()` raises `asyncio.run()
   cannot be called from a running event loop`. Import the module and await
   the coroutine directly instead of running the script's `__main__` block:
   ```python
   from generate_airports_raw import ExtractInternationalAirportsData, URL

   OUTPUT_PATH = "airports_raw.json"   # or a Drive path
   extractor = ExtractInternationalAirportsData(URL, OUTPUT_PATH)
   data = await extractor.scrape()
   with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
       import json
       json.dump(data, f, ensure_ascii=False, indent=2)
   ```


