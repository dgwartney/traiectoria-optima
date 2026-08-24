"""Resolve airport coordinates by scraping each airport's Wikipedia page.

Earlier versions of this script queried the Wikipedia `action=query` API in
batches for coordinates, which reliably hit 429 (rate limit) responses
partway through a run. This instead fetches each airport's own article page
(the `href` already captured by `generate_airports_raw.py`) and reads the
degrees/minutes/seconds coordinates out of the standard `.geo-dms` markup
that Wikipedia's {{Coord}} template renders, e.g.:

    <span class="geo-dms" ...>
      <span class="latitude">36°41'27.65"N</span>
      <span class="longitude">003°12'55.47"E</span>
    </span>

and converts each to decimal degrees.
"""

import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request


class AirportCoordFetcher:
    """Fetches airport coordinates from Wikipedia article pages."""

    HEADERS = {"User-Agent": "airport-coord-fetcher/1.0 (contact: local dev)"}

    DMS_RE = re.compile(
        r"(?P<deg>\d+(?:\.\d+)?)\xb0"
        r"(?:(?P<min>\d+(?:\.\d+)?)′)?"
        r"(?:(?P<sec>\d+(?:\.\d+)?)″)?"
        r"(?P<dir>[NSEW])"
    )

    GEO_DMS_RE = re.compile(
        r'class="geo-dms"[^>]*>\s*'
        r'<span class="latitude"[^>]*>([^<]+)</span>\s*'
        r'<span class="longitude"[^>]*>([^<]+)</span>'
    )

    def __init__(self, raw_path: str, output_path: str) -> None:
        """Configure the input airport list and the output CSV path.

        Args:
            raw_path: Path to the `airports_raw.json` file produced by
                `generate_airports_raw.py`.
            output_path: File path the resulting CSV is written to.
        """
        self.raw_path = raw_path
        self.output_path = output_path

    def dms_to_decimal(self, text: str) -> float:
        """Convert a Wikipedia DMS coordinate string to decimal degrees.

        Args:
            text: A string like `36°41′27.65″N`.

        Returns:
            Signed decimal degrees as a float.
        """
        m = self.DMS_RE.match(text.strip())
        if not m:
            raise ValueError(f"unrecognized coordinate format: {text!r}")
        deg = float(m.group("deg"))
        minutes = float(m.group("min") or 0)
        seconds = float(m.group("sec") or 0)
        value = deg + minutes / 60 + seconds / 3600
        if m.group("dir") in ("S", "W"):
            value = -value
        return value

    def encode_url(self, url: str) -> str:
        """Percent-encode non-ASCII characters in a URL's path/query.

        Article hrefs may contain literal Unicode characters (e.g. `Umeå`),
        which `http.client` cannot send as-is on the request line.

        Args:
            url: The URL to encode.

        Returns:
            The URL with its path and query percent-encoded.
        """
        parts = urllib.parse.urlsplit(url)
        path = urllib.parse.quote(parts.path, safe="/%")
        query = urllib.parse.quote(parts.query, safe="=&%")
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))

    def fetch_page(self, url: str) -> str:
        """Download a URL's HTML.

        Args:
            url: The page to fetch.

        Returns:
            The response body decoded as UTF-8.
        """
        req = urllib.request.Request(self.encode_url(url), headers=self.HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def fetch_coords(self, url: str) -> tuple[float, float] | None:
        """Fetch an airport's article page and extract its coordinates.

        Args:
            url: The airport's Wikipedia article URL.

        Returns:
            A `(lat, lon)` tuple of decimal degrees, or `None` if the page
            has no `.geo-dms` coordinates.
        """
        html = self.fetch_page(url)
        m = self.GEO_DMS_RE.search(html)
        if not m:
            return None
        lat_text, lon_text = m.groups()
        return self.dms_to_decimal(lat_text), self.dms_to_decimal(lon_text)

    def fetch_all_coords(self, urls: list[str]) -> dict:
        """Fetch coordinates for each URL, retrying on rate-limit responses.

        Args:
            urls: Wikipedia article URLs to fetch.

        Returns:
            dict mapping each URL to a `(lat, lon)` tuple, or `None` if
            coordinates could not be resolved.
        """
        total = len(urls)
        start = time.monotonic()
        coords_by_url = {}
        for i, url in enumerate(urls, start=1):
            for attempt in range(5):
                try:
                    coords_by_url[url] = self.fetch_coords(url)
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        wait = 10 * (attempt + 1)
                        print(f"429 on {url}, retrying in {wait}s", flush=True)
                        time.sleep(wait)
                    else:
                        print(f"error fetching {url}: {e}", flush=True)
                        coords_by_url[url] = None
                        break
                except Exception as e:
                    print(f"error fetching {url}: {e}", flush=True)
                    coords_by_url[url] = None
                    break
            else:
                coords_by_url[url] = None

            elapsed = time.monotonic() - start
            rate = i / elapsed if elapsed else 0
            eta = (total - i) / rate if rate else 0
            print(
                f"{i}/{total} pages fetched "
                f"({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)",
                flush=True,
            )
            time.sleep(0.5)
        return coords_by_url

    def run(self) -> None:
        """Resolve coordinates for every airport and write the output CSV."""
        with open(self.raw_path) as f:
            results = json.load(f)["results"]

        urls = sorted({r["href"] for r in results})
        coords_by_url = self.fetch_all_coords(urls)

        missing = 0
        with open(self.output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["location", "airport", "iata", "latitude", "longitude", "region"])
            for r in results:
                coords = coords_by_url.get(r["href"])
                if coords:
                    lat, lon = coords
                else:
                    lat, lon = "", ""
                    missing += 1
                writer.writerow([r["location"], r["airport"], r.get("iata", ""), lat, lon, r["region"]])

        print(f"missing coords: {missing} of {len(results)}", flush=True)


RAW_PATH = "airports_raw.json"
OUTPUT_PATH = "data/processed/international_airports.csv"


if __name__ == "__main__":
    AirportCoordFetcher(RAW_PATH, OUTPUT_PATH).run()
