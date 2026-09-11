"""Re-check the IATA code override table against IATA's official registry.

`data/reference/iata_code_overrides.csv` records, for each scraped airport code
that does not join against OurAirports, whether IATA's registry recognises the
code. Those verdicts came from a live lookup and therefore have a shelf life.
This script re-runs them.

It is an audit tool, not part of the data pipeline: no Makefile data target
depends on it. Run it by hand (`make verify_iata_codes`) when the override table
is suspected stale. Exits non-zero if any code's verdict has changed.

Uses the async Playwright API for the same reason `generate_airports_raw.py`
does, so it can also be awaited directly from a notebook cell:
`await VerifyIataCodes(OVERRIDES_PATH).check_all()`.
"""

import argparse
import asyncio
import sys

import pandas as pd
from playwright.async_api import async_playwright

SEARCH_URL = (
    "https://www.iata.org/en/publications/directories/code-search/?airport.search={code}"
)

# Courtesy delay between lookups; the table holds ten codes.
REQUEST_DELAY_SECONDS = 0.4


class VerifyIataCodes:
    """Checks each override's recorded IATA verdict against the live registry."""

    # A miss renders no <table> at all, alongside the text "No Airport Code
    # found"; a hit renders one row per match, up to five. Matching on the code
    # cell rather than assuming a single row matters: searching "NAN" returns
    # Nadi, Nan and Nanning.
    EXTRACT_JS = """
        () => {
          const table = document.querySelector('table');
          if (!table) return null;
          return [...table.querySelectorAll('tbody tr')].map(
            tr => [...tr.querySelectorAll('td')].map(td => td.textContent.trim())
                    .filter(Boolean));
        }
    """

    def __init__(self, overrides_path: str) -> None:
        """Configure the override table to check.

        Args:
            overrides_path: Path to `iata_code_overrides.csv`.
        """
        self.overrides_path = overrides_path

    async def lookup(self, page, code: str) -> list[list[str]] | None:
        """Search the registry for one airport code.

        Args:
            page: The Playwright page to navigate.
            code: The three-letter code to search for.

        Returns:
            A list of `[city, airport, code]` rows, or `None` if the registry
            returned no result table at all.
        """
        await page.goto(SEARCH_URL.format(code=code), wait_until="networkidle")
        return await page.evaluate(self.EXTRACT_JS)

    async def check_all(self) -> list[tuple[str, str, str, list]]:
        """Look up every code in the override table.

        Returns:
            A list of `(code, expected, actual, rows)` tuples, where `expected`
            and `actual` are either `valid` or `not-found`.
        """
        overrides = pd.read_csv(self.overrides_path)
        outcomes = []
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            for row in overrides.itertuples():
                code = row.wiki_iata.strip().upper()
                rows = await self.lookup(page, code)
                matched = [r for r in (rows or []) if code in r]
                actual = "valid" if matched else "not-found"
                outcomes.append((code, row.iata_registry.strip(), actual, matched))
                await asyncio.sleep(REQUEST_DELAY_SECONDS)
            await browser.close()
        return outcomes

    def report(self, outcomes: list[tuple[str, str, str, list]]) -> int:
        """Print one verdict per code and summarise.

        Args:
            outcomes: The result of `check_all`.

        Returns:
            Process exit status: 0 if every verdict still holds, 1 otherwise.
        """
        drifted = []
        for code, expected, actual, matched in outcomes:
            mark = "ok  " if expected == actual else "DRIFT"
            detail = f" — {matched[0][0]} / {matched[0][1]}" if matched else ""
            print(f"{mark} {code}: recorded {expected}, registry says {actual}{detail}")
            if expected != actual:
                drifted.append(code)

        print(f"\n{len(outcomes)} codes checked, {len(drifted)} drifted")
        if drifted:
            print(f"update {self.overrides_path} for: {', '.join(drifted)}")
            return 1
        return 0

    async def run(self) -> int:
        """Check every code and report.

        Returns:
            Process exit status.
        """
        return self.report(await self.check_all())


def parse_args() -> argparse.Namespace:
    """Parse the override table path from the command line.

    Returns:
        A namespace with an `overrides_path` attribute.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "overrides_path",
        nargs="?",
        default="data/reference/iata_code_overrides.csv",
        help="Path to the IATA code override table.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(VerifyIataCodes(parse_args().overrides_path).run()))
