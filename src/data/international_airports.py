"""Build international_airports.csv by joining the scrape against OurAirports.

The scraped airport list (`airports_raw.json`, produced by
`generate_airports_raw.py`) carries no coordinates. Earlier versions resolved
them by issuing one HTTP request per airport to AirportsAPI.com; that API turned
out to be serving OurAirports data back over the network, bit-identically for
99.6% of rows and *wrongly* for three of them. So coordinates now come straight
from `data/raw/our_airports/airports.csv`, which the project already vendors.

Ten scraped codes do not join, because Wikipedia and OurAirports disagree about
the IATA code or because neither assigns one. Each was checked against IATA's
official registry and resolved by hand into
`data/reference/iata_code_overrides.csv`, which maps the scraped code to an
OurAirports `ident`. See `docs/data.md` for the table and the reasoning.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd

# Columns of the output CSV, in the order `flight_data.py` loads them into the
# `intl_airports` table.
OUTPUT_COLUMNS = ["location", "airport", "iata", "latitude", "longitude", "region"]


class InternationalAirportsBuilder:
    """Joins the scraped airport list to OurAirports coordinates."""

    def __init__(
        self,
        raw_path: str,
        our_airports_path: str,
        overrides_path: str,
        output_path: str,
    ) -> None:
        """Configure the three inputs and the output path.

        Args:
            raw_path: Path to `airports_raw.json` from `generate_airports_raw.py`.
            our_airports_path: Path to the OurAirports `airports.csv`.
            overrides_path: Path to the hand-curated IATA override table.
            output_path: File path the resulting CSV is written to.
        """
        self.raw_path = raw_path
        self.our_airports_path = our_airports_path
        self.overrides_path = overrides_path
        self.output_path = output_path

    @staticmethod
    def normalise(codes: pd.Series) -> pd.Series:
        """Upper-case and strip a column of IATA codes.

        Uses `fillna` rather than `astype(str)` deliberately: Nadi International
        Airport's IATA code is literally `NAN`, and `astype(str)` on a missing
        value can produce that same string, folding a real airport in with the
        blanks.

        Args:
            codes: Column of IATA codes, possibly containing missing values.

        Returns:
            The column with missing values as empty strings, stripped and
            upper-cased.
        """
        return codes.fillna("").str.strip().str.upper()

    def load_airports(self) -> pd.DataFrame:
        """Read the OurAirports data, indexed for both lookup paths.

        Returns:
            The OurAirports frame with an added normalised `code` column.
        """
        airports = pd.read_csv(
            self.our_airports_path,
            low_memory=False,
            usecols=["ident", "iata_code", "latitude_deg", "longitude_deg"],
        )
        airports["code"] = self.normalise(airports["iata_code"])
        return airports

    def load_overrides(self) -> tuple[dict[str, str], dict[str, str]]:
        """Read the override table.

        Returns:
            A `(idents, canonical)` pair. `idents` maps each scraped code to the
            OurAirports `ident` its coordinates come from. `canonical` maps the
            scraped code to the code that should appear in the output, and holds
            an entry only where the two differ.
        """
        overrides = pd.read_csv(self.overrides_path)
        codes = self.normalise(overrides["wiki_iata"])
        idents = dict(
            zip(codes, overrides["ourairports_ident"].str.strip(), strict=True)
        )
        canonical = {
            code: replacement
            for code, replacement in zip(
                codes, self.normalise(overrides["canonical_iata"]), strict=True
            )
            if replacement
        }
        return idents, canonical

    def resolve(self, results: list[dict]) -> tuple[list[list], list[dict]]:
        """Attach coordinates to every scraped airport.

        Args:
            results: The `results` list from `airports_raw.json`.

        Returns:
            A `(rows, unresolved)` pair, where `rows` are the output records and
            `unresolved` lists the scraped entries no lookup could resolve.

        Raises:
            SystemExit: If an override names an unknown `ident`, or names a code
                that no longer appears in the scrape.
        """
        airports = self.load_airports()
        overrides, canonical = self.load_overrides()

        by_ident = airports.set_index("ident")
        with_code = airports[airports["code"] != ""]
        by_code = with_code.drop_duplicates("code").set_index("code")

        self.check_overrides(overrides, by_ident.index, results)

        rows, unresolved = [], []
        for entry in results:
            code = (entry.get("iata") or "").strip().upper()
            if code in overrides:
                source = by_ident.loc[overrides[code]]
            elif code in by_code.index:
                source = by_code.loc[code]
            else:
                source = None
                unresolved.append(entry)

            latitude = "" if source is None else source["latitude_deg"]
            longitude = "" if source is None else source["longitude_deg"]
            rows.append(
                [
                    entry["location"],
                    entry["airport"],
                    canonical.get(code, code),
                    latitude,
                    longitude,
                    entry["region"],
                ]
            )
        return rows, unresolved

    def check_overrides(self, overrides: dict, idents, results: list[dict]) -> None:
        """Fail if the override table has drifted out of sync with its inputs.

        A rescrape or a refreshed OurAirports snapshot should surface the drift
        rather than silently skipping a row.

        Args:
            overrides: Mapping of scraped code to OurAirports `ident`.
            idents: Index of every `ident` present in OurAirports.
            results: The scraped entries.

        Raises:
            SystemExit: If any override is stale.
        """
        known = set(idents)
        missing = {c: i for c, i in overrides.items() if i not in known}
        if missing:
            joined = ", ".join(f"{c} -> {i}" for c, i in sorted(missing.items()))
            sys.exit(f"override names unknown OurAirports ident: {joined}")

        scraped = {(r.get("iata") or "").strip().upper() for r in results}
        unused = sorted(set(overrides) - scraped)
        if unused:
            sys.exit(f"override code no longer present in the scrape: {', '.join(unused)}")

    def report(self, unresolved: list[dict], total: int, override_count: int) -> None:
        """Print the outcome of every lookup.

        A clean run says so positively rather than printing nothing, and an
        unclean one names each airport in full so the failure is actionable
        without opening the CSV.

        Args:
            unresolved: Scraped entries left without coordinates.
            total: Number of scraped entries.
            override_count: Number of entries resolved via the override table.
        """
        if not unresolved:
            print(
                f"all {total} airports resolved "
                f"({override_count} via {self.overrides_path})"
            )
        else:
            print(f"unmatched airports — no coordinates resolved "
                  f"({len(unresolved)} of {total}):\n")
            rows = sorted(
                (
                    (r.get("iata") or "(none)").strip().upper() or "(none)",
                    r["region"],
                    r["location"],
                    r["airport"],
                )
                for r in unresolved
            )
            headers = ("IATA", "REGION", "LOCATION", "AIRPORT")
            widths = [
                max(len(h), *(len(row[i]) for row in rows))
                for i, h in enumerate(headers)
            ]
            fmt = "  " + "  ".join(f"{{:<{w}}}" for w in widths)
            print(fmt.format(*headers).rstrip())
            print(fmt.format(*("-" * len(h) for h in headers)).rstrip())
            for row in rows:
                print(fmt.format(*row).rstrip())
            print()

        print(f"missing coords: {len(unresolved)} of {total}", flush=True)

    def run(self) -> None:
        """Resolve coordinates for every airport and write the output CSV."""
        with open(self.raw_path, encoding="utf-8") as f:
            results = json.load(f)["results"]

        rows, unresolved = self.resolve(results)

        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(OUTPUT_COLUMNS)
            writer.writerows(rows)

        overrides, _ = self.load_overrides()
        scraped = [(r.get("iata") or "").strip().upper() for r in results]
        self.report(unresolved, len(results), sum(c in overrides for c in scraped))


def parse_args() -> argparse.Namespace:
    """Parse the input and output paths from the command line.

    Returns:
        A namespace with `raw_path`, `our_airports_path`, `overrides_path` and
        `output_path` attributes.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "raw_path",
        help="Path to the airports_raw.json file produced by generate_airports_raw.py.",
    )
    parser.add_argument(
        "our_airports_path",
        help="Path to the OurAirports airports.csv file.",
    )
    parser.add_argument(
        "overrides_path",
        help="Path to the IATA code override table.",
    )
    parser.add_argument("output_path", help="File path the resulting CSV is written to.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    InternationalAirportsBuilder(
        args.raw_path, args.our_airports_path, args.overrides_path, args.output_path
    ).run()
