"""Resolve airport coordinates via the AirportsAPI.com lookup endpoint.

AirportsAPI.com (https://airportsapi.com) requires no auth and resolves an
IATA code directly to coordinates via `GET /api/airports/{code}`, e.g.:

    {"data": {"attributes": {"latitude": 51.4706, "longitude": -0.461941, ...}}}

Requests run concurrently (bounded by CONCURRENCY) via httpx.AsyncClient,
since each lookup is a single independent HTTP call.

For the Wikipedia-scraping approach (kept around since it can also be
extended to collect other data off each airport's page), see
fetch_airport_coords.py.
"""

import argparse
import asyncio
import csv
import json
import time

import httpx


class AirportCoordApiFetcher:
    """Fetches airport coordinates from AirportsAPI.com by IATA code."""

    API_URL = "https://airportsapi.com/api/airports/{code}"
    HEADERS = {"User-Agent": "airport-coord-fetcher/1.0 (contact: local dev)", "Accept": "application/json"}
    CONCURRENCY = 5

    def __init__(self, raw_path: str, output_path: str) -> None:
        """Configure the input airport list and the output CSV path.

        Args:
            raw_path: Path to the `airports_raw.json` file produced by
                `generate_airports_raw.py`.
            output_path: File path the resulting CSV is written to.
        """
        self.raw_path = raw_path
        self.output_path = output_path

    async def fetch_coords(self, client: httpx.AsyncClient, iata: str) -> tuple[float, float] | None:
        """Look up an airport's coordinates by IATA code.

        Args:
            client: The shared httpx client to issue the request on.
            iata: The airport's IATA code, e.g. `LHR`.

        Returns:
            A `(lat, lon)` tuple of decimal degrees, or `None` if the API
            has no record for this code.
        """
        url = self.API_URL.format(code=iata)
        resp = await client.get(url, headers=self.HEADERS, timeout=30)
        resp.raise_for_status()
        attrs = resp.json()["data"]["attributes"]
        lat, lon = attrs.get("latitude"), attrs.get("longitude")
        if lat is None or lon is None:
            return None
        return lat, lon

    async def fetch_one(
        self, client: httpx.AsyncClient, sem: asyncio.Semaphore, iata: str
    ) -> tuple[str, tuple[float, float] | None]:
        """Fetch one IATA code's coordinates, retrying on rate-limit responses.

        Args:
            client: The shared httpx client to issue requests on.
            sem: Semaphore bounding overall concurrency.
            iata: The airport's IATA code.

        Returns:
            A `(iata, coords)` pair, where `coords` is `None` if the
            lookup ultimately failed.
        """
        async with sem:
            for attempt in range(5):
                try:
                    return iata, await self.fetch_coords(client, iata)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        print(f"no record for {iata}", flush=True)
                        return iata, None
                    if e.response.status_code == 429:
                        wait = 10 * (attempt + 1)
                        print(f"429 on {iata}, retrying in {wait}s", flush=True)
                        await asyncio.sleep(wait)
                    else:
                        print(f"error fetching {iata}: {e}", flush=True)
                        return iata, None
                except Exception as e:
                    print(f"error fetching {iata}: {e}", flush=True)
                    return iata, None
            return iata, None

    async def fetch_all_coords(self, iata_codes: list[str]) -> dict:
        """Fetch coordinates for every IATA code concurrently.

        Args:
            iata_codes: Airport IATA codes to look up.

        Returns:
            dict mapping each IATA code to a `(lat, lon)` tuple, or `None`
            if coordinates could not be resolved.
        """
        total = len(iata_codes)
        start = time.monotonic()
        sem = asyncio.Semaphore(self.CONCURRENCY)
        coords_by_iata = {}
        async with httpx.AsyncClient() as client:
            tasks = [asyncio.create_task(self.fetch_one(client, sem, iata)) for iata in iata_codes]
            for i, task in enumerate(asyncio.as_completed(tasks), start=1):
                iata, coords = await task
                coords_by_iata[iata] = coords
                elapsed = time.monotonic() - start
                rate = i / elapsed if elapsed else 0
                eta = (total - i) / rate if rate else 0
                print(
                    f"{i}/{total} airports fetched "
                    f"({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)",
                    flush=True,
                )
        return coords_by_iata

    def run(self) -> None:
        """Resolve coordinates for every airport and write the output CSV."""
        with open(self.raw_path) as f:
            results = json.load(f)["results"]

        iata_codes = sorted({r["iata"] for r in results if r.get("iata")})
        coords_by_iata = asyncio.run(self.fetch_all_coords(iata_codes))

        missing = 0
        with open(self.output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["location", "airport", "iata", "latitude", "longitude", "region"])
            for r in results:
                coords = coords_by_iata.get(r.get("iata"))
                if coords:
                    lat, lon = coords
                else:
                    lat, lon = "", ""
                    missing += 1
                writer.writerow([r["location"], r["airport"], r.get("iata", ""), lat, lon, r["region"]])

        print(f"missing coords: {missing} of {len(results)}", flush=True)


def parse_args() -> argparse.Namespace:
    """Parse the input and output paths from the command line.

    Returns:
        A namespace with `raw_path` and `output_path` attributes.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "raw_path",
        help="Path to the airports_raw.json file produced by generate_airports_raw.py.",
    )
    parser.add_argument("output_path", help="File path the resulting CSV is written to.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(f"{args.raw_path = }, {args.output_path = }")
    AirportCoordApiFetcher(args.raw_path, args.output_path).run()
