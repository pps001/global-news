#!/usr/bin/env python3
"""Collect the newest headlines for each country from GDELT and write news.json.

Run by .github/workflows/update-news.yml every 30 minutes. Uses only the Python
standard library. Usage: python scripts/fetch_news.py news.json

For each country it asks GDELT for the newest English-language articles from that
country's press over the last 3 days; if there are none in English it takes any
language. Countries that fail this run keep their previous headlines.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# Country code used by the page -> GDELT source-country name (spaces removed) or FIPS code.
# To add a country, add it here AND to the COUNTRIES list in index.html (with its lon/lat).
COUNTRIES = {
    "USA": "unitedstates", "CAN": "canada", "MEX": "mexico", "BRA": "brazil", "ARG": "argentina",
    "GBR": "unitedkingdom", "IRL": "ireland", "FRA": "france", "DEU": "germany", "ESP": "spain",
    "PRT": "portugal", "ITA": "italy", "NLD": "netherlands", "BEL": "belgium", "CHE": "switzerland",
    "AUT": "austria", "DNK": "denmark", "NOR": "norway", "SWE": "sweden", "FIN": "finland",
    "POL": "poland", "CZE": "EZ", "HUN": "hungary", "ROU": "romania", "SRB": "serbia",
    "GRC": "greece", "MDA": "moldova", "UKR": "ukraine", "RUS": "russia", "TUR": "turkey",
    "EGY": "egypt", "MAR": "morocco", "DZA": "algeria", "TUN": "tunisia", "SEN": "senegal",
    "GHA": "ghana", "CIV": "IV", "NGA": "nigeria", "CMR": "cameroon", "SDN": "sudan",
    "ETH": "ethiopia", "KEN": "kenya", "UGA": "uganda", "RWA": "rwanda", "TZA": "tanzania",
    "COD": "CG", "AGO": "angola", "ZMB": "zambia", "ZWE": "zimbabwe", "ZAF": "southafrica",
    "ISR": "israel", "SAU": "saudiarabia", "IRN": "iran", "PAK": "pakistan", "IND": "india",
    "CHN": "china", "KOR": "southkorea", "JPN": "japan", "PHL": "philippines", "MYS": "malaysia",
    "SGP": "SN", "IDN": "indonesia", "AUS": "australia", "NZL": "newzealand",
}

API = "https://api.gdeltproject.org/api/v2/doc/doc"
GAP_SECONDS = 5.5          # GDELT asks for no more than one request every 5 seconds
PER_COUNTRY = 3


def gdelt(code: str, english_only: bool) -> list:
    query = f"sourcecountry:{code}" + (" sourcelang:english" if english_only else "")
    url = API + "?" + urllib.parse.urlencode({
        "format": "json", "mode": "artlist", "sort": "datedesc",
        "timespan": "3d", "maxrecords": "15", "query": query,
    })
    for attempt in range(3):
        req = urllib.request.Request(url, headers={"User-Agent": "world-news-globe/1.0 (GitHub Action)"})
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as err:
            if err.code == 429:                       # throttled: back off and retry
                time.sleep(10 * (attempt + 1))
                continue
            raise
        try:
            return json.loads(body).get("articles") or []
        except json.JSONDecodeError:
            if "limit requests" in body.lower():      # throttle message sent as plain text
                time.sleep(10 * (attempt + 1))
                continue
            if not body.strip():                      # GDELT returns an empty body when nothing matches
                return []
            raise ValueError("unexpected reply: " + body[:120])
    raise RuntimeError("still rate-limited after retries")


def seen_iso(s: str) -> str:
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return ""


def to_items(articles: list) -> list:
    seen, out = set(), []
    for a in articles:
        title = " ".join((a.get("title") or "").split())
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        out.append({"t": title, "s": a.get("domain", ""), "d": seen_iso(a.get("seendate", "")), "u": a.get("url", "")})
        if len(out) == PER_COUNTRY:
            break
    return out


def main(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            previous = json.load(f).get("countries", {})
    except (OSError, ValueError):
        previous = {}

    countries, fresh, failed = {}, 0, []
    for iso, code in COUNTRIES.items():
        items = []
        try:
            items = to_items(gdelt(code, english_only=True))
            if not items:
                time.sleep(GAP_SECONDS)
                items = to_items(gdelt(code, english_only=False))
        except Exception as err:  # keep going; one bad country should not sink the run
            failed.append(f"{iso}: {err}")
        if items:
            countries[iso] = items
            fresh += 1
        elif previous.get(iso):
            countries[iso] = previous[iso]
        time.sleep(GAP_SECONDS)

    print(f"Fresh headlines for {fresh}/{len(COUNTRIES)} countries.")
    for line in failed:
        print("  failed", line)
    if fresh == 0:
        print("Nothing fetched; leaving news.json unchanged.")
        return 1

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "GDELT 2.0 DOC API", "countries": countries}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "news.json"))
