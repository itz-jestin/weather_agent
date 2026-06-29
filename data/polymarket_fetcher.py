"""
data/polymarket_fetcher.py
Fetches weather-related prediction markets from Polymarket's public Gamma API.
No API key required for read-only access.
"""

from __future__ import annotations

import httpx
from typing import Any

from config import POLYMARKET_GAMMA_URL, CITIES

WEATHER_KEYWORDS = [
    "temperature", "rain", "precipitation", "weather", "storm",
    "snow", "wind", "hurricane", "tornado", "flood",
]

# City names used as additional search terms
CITY_NAMES = [c["name"].lower() for c in CITIES]


def _get(path: str, params: dict | None = None) -> Any:
    url = POLYMARKET_GAMMA_URL + path
    try:
        r = httpx.get(url, params=params or {}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        print(f"[polymarket] error fetching {url}: {exc}")
        return [] if "markets" in path else {}


import httpx

def fetch_weather_markets():

    params = {
        "active": "true",
        "closed": "false",
        "limit": 500,
    }

    try:
        r = httpx.get(
            POLYMARKET_GAMMA_URL + "/markets",
            params=params,
            timeout=httpx.Timeout(30),
        )

        r.raise_for_status()

        markets = r.json()

        weather = []

        for m in markets:
            q = m.get("question", "").lower()

            if any(k in q for k in WEATHER_KEYWORDS):
                weather.append(m)

        print(f"[polymarket] Found {len(weather)} weather markets")

        return weather

    except Exception as e:
        print(e)
        from data.mock_data import MOCK_MARKETS
        return MOCK_MARKETS

def parse_market(market: dict) -> dict:
    """
    Normalise a raw Polymarket market dict into a concise trading record.
    """
    # Probability of YES outcome (0-1)
    outcomes    = market.get("outcomes", [])
    out_prices  = market.get("outcomePrices", [])

    yes_prob = 0.5  # default
    if outcomes and out_prices:
        for i, o in enumerate(outcomes):
            if str(o).upper() == "YES" and i < len(out_prices):
                try:
                    yes_prob = float(out_prices[i])
                except ValueError:
                    pass

    return {
        "id":          market.get("conditionId") or market.get("id"),
        "question":    market.get("question", ""),
        "category":    market.get("category", ""),
        "end_date":    market.get("endDate", ""),
        "yes_prob":    yes_prob,
        "no_prob":     round(1.0 - yes_prob, 4),
        "volume":      market.get("volume", 0),
        "liquidity":   market.get("liquidity", 0),
        "matched_city": market.get("matched_city"),
        "url":         f"https://polymarket.com/event/{market.get('slug', '')}",
    }


def fetch_parsed_markets():
    raw = fetch_weather_markets()

    # If we're already using mock markets, return them directly.
    if raw and isinstance(raw, list) and "question" in raw[0]:
        return raw

    parsed = [parse_market(m) for m in raw]

    liquid = [m for m in parsed if (m.get("liquidity") or 0) > 10]

    if not liquid:
        print("[polymarket] No live markets found. Using mock markets.")
        from data.mock_data import MOCK_MARKETS
        return MOCK_MARKETS

    return liquid