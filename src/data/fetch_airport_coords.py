import json
import urllib.parse
import urllib.request
import csv
import time

with open("airports_raw.json") as f:
    data = json.load(f)

results = data["results"]

def title_from_href(href):
    title = href.split("/wiki/")[-1]
    return urllib.parse.unquote(title).replace("_", " ")

titles = sorted({title_from_href(r["href"]) for r in results})

coords = {}
redirects = {}
normalized = {}

API = "https://en.wikipedia.org/w/api.php"

def fetch_batch(batch):
    params = {
        "action": "query",
        "titles": "|".join(batch),
        "prop": "coordinates",
        "format": "json",
        "redirects": 1,
        "colimit": "max",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "airport-coord-fetcher/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

BATCH_SIZE = 50
for i in range(0, len(titles), BATCH_SIZE):
    batch = titles[i:i+BATCH_SIZE]
    for attempt in range(5):
        try:
            j = fetch_batch(batch)
            break
        except Exception as e:
            print("retry", i, e)
            time.sleep(5 * (attempt + 1))
    else:
        print("FAILED batch", i)
        continue

    q = j.get("query", {})
    for norm in q.get("normalized", []):
        normalized[norm["from"]] = norm["to"]
    for redir in q.get("redirects", []):
        redirects[redir["from"]] = redir["to"]
    for pageid, page in q.get("pages", {}).items():
        title = page.get("title")
        coordlist = page.get("coordinates")
        if coordlist:
            coords[title] = (coordlist[0]["lat"], coordlist[0]["lon"])
    print(f"batch {i}-{i+len(batch)} done, total coords so far: {len(coords)}")
    time.sleep(1)

def resolve(title):
    t = normalized.get(title, title)
    t = redirects.get(t, t)
    return coords.get(t)

with open("data/processed/international_airports.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["location", "airport", "latitude", "longitude", "region"])
    missing = 0
    for r in results:
        title = title_from_href(r["href"])
        c = resolve(title)
        if not c:
            missing += 1
            lat, lon = "", ""
        else:
            lat, lon = c
        writer.writerow([r["location"], r["airport"], lat, lon, r["region"]])
    print("missing coords:", missing, "of", len(results))
