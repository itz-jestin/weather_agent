"""
data/weather_fetcher.py
Fetches weather data from two sources:
  1. Open-Meteo (free, no API key) – global forecast + historical
  2. Apify Weather API actor         – local / hyper-local data
"""

from __future__ import annotations

import datetime
import httpx
from typing import Any

from config import APIFY_TOKEN, CITIES


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_HIST = "https://archive-api.open-meteo.com/v1/archive"

# Apify actor ID for the weather database scraper
APIFY_ACTOR = "oneary/weather-database-scraper"


# ── helpers ──────────────────────────────────────────────────────────────────

def _get(url: str, params: dict) -> dict:
    """Synchronous HTTP GET with basic error handling."""
    try:
        r = httpx.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        print(f"[weather_fetcher] HTTP error: {exc}")
        return {}


# ── Open-Meteo ────────────────────────────────────────────────────────────────

def fetch_forecast(city: dict, days: int = 7) -> dict[str, Any]:
    """
    Fetch 7-day hourly forecast for a city via Open-Meteo.

    Returns a dict with:
        city, temperature_2m (list), precipitation (list),
        windspeed_10m (list), time (list)
    """
    params = {
        "latitude":  city["lat"],
        "longitude": city["lon"],
        "hourly":    "temperature_2m,precipitation,windspeed_10m,weathercode",
        "forecast_days": days,
        "timezone":  "auto",
    }
    raw = _get(OPEN_METEO_URL, params)
    hourly = raw.get("hourly", {})
    return {
        "city":            city["name"],
        "country":         city["country"],
        "time":            hourly.get("time", []),
        "temperature_2m":  hourly.get("temperature_2m", []),
        "precipitation":   hourly.get("precipitation", []),
        "windspeed_10m":   hourly.get("windspeed_10m", []),
        "weathercode":     hourly.get("weathercode", []),
    }


def fetch_historical(city: dict, days_back: int = 30) -> dict[str, Any]:
    """
    Fetch historical daily weather for a city (last `days_back` days).
    Used for calibrating the prediction model.
    """
    end   = datetime.date.today() - datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=days_back)
    params = {
        "latitude":   city["lat"],
        "longitude":  city["lon"],
        "start_date": str(start),
        "end_date":   str(end),
        "daily":      "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
        "timezone":   "auto",
    }
    raw   = _get(OPEN_METEO_HIST, params)
    daily = raw.get("daily", {})
    return {
        "city":                city["name"],
        "country":             city["country"],
        "time":                daily.get("time", []),
        "temp_max":            daily.get("temperature_2m_max", []),
        "temp_min":            daily.get("temperature_2m_min", []),
        "precipitation_sum":   daily.get("precipitation_sum", []),
        "windspeed_max":       daily.get("windspeed_10m_max", []),
    }


def fetch_daily_summary(city: dict) -> dict[str, Any]:
    """
    Returns today's forecast as a single summary dict:
        max_temp, min_temp, total_precip, max_wind, will_rain
    """
    forecast = fetch_forecast(city, days=2)
    temps    = forecast["temperature_2m"]
    precip   = forecast["precipitation"]
    wind     = forecast["windspeed_10m"]

    if not temps:
        return {"city": city["name"], "error": "no data"}

    # today = first 24 entries (hourly)
    today_temps  = [t for t in temps[:24]  if t is not None]
    today_precip = [p for p in precip[:24] if p is not None]
    today_wind   = [w for w in wind[:24]   if w is not None]

    return {
        "city":        city["name"],
        "country":     city["country"],
        "max_temp_c":  max(today_temps)  if today_temps  else None,
        "min_temp_c":  min(today_temps)  if today_temps  else None,
        "total_precip_mm": sum(today_precip) if today_precip else 0.0,
        "max_wind_kmh":    max(today_wind)   if today_wind   else None,
        "will_rain":   sum(today_precip) > 0.5 if today_precip else False,
    }


# ── Apify (optional, enriches data) ──────────────────────────────────────────

def fetch_apify_weather(city: dict) -> dict[str, Any]:
    """
    Scrape localised weather from Apify actor.
    Falls back to empty dict if APIFY_TOKEN is not set.
    """
    if not APIFY_TOKEN:
        return {"city": city["name"], "source": "apify", "data": None,
                "note": "No APIFY_TOKEN set – skipped"}

    try:
        from apify_client import ApifyClient  # type: ignore
        client = ApifyClient(APIFY_TOKEN)
        run_input = {
            "locations": [city["name"]],
            "units": "metric",
        }
        run    = client.actor(APIFY_ACTOR).call(run_input=run_input)
        items  = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return {"city": city["name"], "source": "apify", "data": items}
    except Exception as exc:
        return {"city": city["name"], "source": "apify", "error": str(exc)}


# ── Bulk fetcher ──────────────────────────────────────────────────────────────

def fetch_all_cities() -> list[dict[str, Any]]:
    """Return summary weather data for every configured city."""
    results = []
    for city in CITIES:
        summary  = fetch_daily_summary(city)
        apify    = fetch_apify_weather(city)
        combined = {**summary, "apify_data": apify.get("data")}
        results.append(combined)
        print(f"  [weather] {city['name']:12s} — max {summary.get('max_temp_c', '?')}°C  "
              f"rain={summary.get('will_rain', '?')}")
    return results
