"""Scrape airport listings from Wikipedia into airports_raw.json.

Regenerates the raw input consumed by fetch_airport_coords.py. Requires
`playwright install --with-deps chromium` once per environment. Uses the
async API so this also works from a notebook
(e.g. Colab) cell, where the sync API can't run inside the already-active
event loop: `data = await ExtractInternationalAirportsData(URL, OUTPUT_PATH).scrape()`.
"""

import asyncio
import json

from playwright.async_api import async_playwright


class ExtractInternationalAirportsData:
    """Scrapes the Wikipedia list of international airports by country."""

    EXTRACT_JS = """
        () => {
          const content = document.querySelector('#mw-content-text .mw-parser-output');
          const results = [];
          let region = null, country = null;
          const allEls = content.querySelectorAll('h2, h3, h4, table.wikitable');
          allEls.forEach(el => {
            if (el.tagName === 'H2') {
              const span = el.querySelector('.mw-headline');
              region = (span ? span.textContent : el.textContent).replace(/\\[edit\\]/g,'').trim();
            } else if (el.tagName === 'H4' || el.tagName === 'H3') {
              const span = el.querySelector('.mw-headline');
              country = (span ? span.textContent : el.textContent).replace(/\\[edit\\]/g,'').trim();
            } else if (el.tagName === 'TABLE') {
              const rows = el.querySelectorAll('tbody tr');
              rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length < 2) return;
                const locLink = cells[0].querySelector('a');
                const airportLink = cells[1].querySelector('a');
                if (!airportLink) return;
                results.push({
                  region,
                  country,
                  location: cells[0].textContent.trim(),
                  airport: airportLink.textContent.trim(),
                  iata: cells.length > 2 ? cells[2].textContent.trim() : null,
                  href: airportLink.getAttribute('href')
                });
              });
            }
          });
          return {count: results.length, results};
        }
    """

    def __init__(self, url: str, output_path: str) -> None:
        """Configure the page to scrape and where to write the result.

        Args:
            url: Wikipedia page listing international airports by country.
            output_path: File path the scraped JSON is written to.
        """
        self.url = url
        self.output_path = output_path

    async def scrape(self) -> dict:
        """Run the extraction against the live Wikipedia page.

        Returns:
            A dict with `count` and `results`, where `results` is a list of
            `{region, country, location, airport, iata, href}` dicts.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(self.url, wait_until="networkidle")
            data = await page.evaluate(self.EXTRACT_JS)
            origin = page.url.split("/wiki/")[0]
            for result in data["results"]:
                if not result["href"].startswith("http"):
                    result["href"] = origin + result["href"]
            await browser.close()
        return data

    async def run(self) -> None:
        """Scrape and write the result to `self.output_path`."""
        data = await self.scrape()
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"wrote {data['count']} results to {self.output_path}")


URL = "https://en.wikipedia.org/wiki/List_of_international_airports_by_country"
OUTPUT_PATH = "airports_raw.json"


if __name__ == "__main__":
    asyncio.run(ExtractInternationalAirportsData(URL, OUTPUT_PATH).run())
