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
