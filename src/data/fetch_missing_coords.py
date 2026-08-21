import json
import re
import time
import urllib.parse
import urllib.request
import csv

API = "https://en.wikipedia.org/w/api.php"

def fetch_geo(title):
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "redirects": 1,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "airport-coord-fetcher/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        j = json.loads(resp.read().decode("utf-8"))
    if "error" in j:
        return None
    html = j["parse"]["text"]["*"]
    m = re.search(r'class="geo">([^<]+)<', html)
    if not m:
        return None
    text = m.group(1).strip()
    parts = re.split(r";\s*", text)
    if len(parts) != 2:
        return None
    try:
        lat, lon = float(parts[0]), float(parts[1])
    except ValueError:
        return None
    return lat, lon

rows = []
with open("data/processed/international_airports.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

with open("airports_raw.json") as f:
    raw = json.load(f)["results"]

def title_from_href(href):
    title = href.split("/wiki/")[-1]
    return urllib.parse.unquote(title).replace("_", " ")

titles_by_key = {}
for r in raw:
    key = (r["location"], r["airport"], r["region"])
    titles_by_key[key] = title_from_href(r["href"])

fixed = 0
still_missing = 0
for row in rows:
    if row["latitude"]:
        continue
    key = (row["location"], row["airport"], row["region"])
    title = titles_by_key.get(key)
    if not title:
        still_missing += 1
        continue
    for attempt in range(6):
        try:
            geo = fetch_geo(title)
            break
        except Exception as e:
            print("retry", title, e)
            time.sleep(10 * (attempt + 1))
    else:
        geo = None
    if geo:
        row["latitude"], row["longitude"] = geo
        fixed += 1
    else:
        still_missing += 1
        print("no coords found:", title)
    time.sleep(2)

print(f"fixed: {fixed}, still missing: {still_missing}")

with open("data/processed/international_airports.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
