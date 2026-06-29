"""
models/prediction_model.py
Builds and runs a simple calibrated prediction model that combines:
  - Open-Meteo forecast data
  - 30-day historical calibration
  - Market-implied probabilities from Polymarket
to produce an estimated TRUE probability for each weather market question.
"""

from __future__ import annotations

import re
import math
from typing import Any

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Feature extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_threshold(question: str) -> tuple[str | None, float | None]:
    """
    Attempt to parse a threshold from the market question.
    Returns (metric, threshold_value) or (None, None).

    Examples handled:
      "Will temperature in London exceed 30°C on June 29?"  → ("temp_above", 30.0)
      "Will it rain in Tokyo on June 30?"                   → ("rain", None)
      "Will New York see a high above 90°F?"                → ("temp_above_f", 90.0)
    """
    q = question.lower()

    # Rain / precipitation
    if any(w in q for w in ("rain", "precipitation", "shower")):
        return ("rain", None)

    # Snow
    if "snow" in q:
        return ("snow", None)

    # Temperature in Celsius
    m = re.search(r"(\d+(?:\.\d+)?)\s*°?c\b", q)
    if m:
        return ("temp_above_c", float(m.group(1)))

    # Temperature in Fahrenheit
    m = re.search(r"(\d+(?:\.\d+)?)\s*°?f\b", q)
    if m:
        return ("temp_above_f", float(m.group(1)))

    # Generic "above/exceed/over N degrees"
    m = re.search(r"(?:above|exceed|over)\s+(\d+(?:\.\d+)?)\s*degrees?", q)
    if m:
        return ("temp_above_c", float(m.group(1)))

    # Wind
    m = re.search(r"wind.*?(\d+(?:\.\d+)?)\s*(?:km/?h|mph)", q)
    if m:
        val = float(m.group(1))
        if "mph" in q:
            val *= 1.609  # convert to km/h
        return ("wind_above", val)

    return (None, None)


def _f_to_c(f: float) -> float:
    return (f - 32) * 5 / 9


# ─────────────────────────────────────────────────────────────────────────────
# Core predictor
# ─────────────────────────────────────────────────────────────────────────────

class WeatherPredictor:
    """
    Lightweight, rule-based + statistical predictor.

    For each market it:
      1. Extracts what the market is asking.
      2. Uses forecast data to compute a model probability.
      3. Blends model probability with historical base-rate.
      4. Returns an 'edge' = model_prob − market_prob.
    """

    def __init__(
        self,
        weather_summaries: list[dict],
        historical_data:   dict[str, dict] | None = None,
    ):
        # Index by city name (lower-case)
        self.summaries: dict[str, dict] = {
            d["city"].lower(): d for d in weather_summaries if "city" in d
        }
        self.historical: dict[str, dict] = historical_data or {}

    # ── historical base-rate ──────────────────────────────────────────────────

    def _rain_base_rate(self, city_key: str) -> float:
        """Fraction of historical days with >0.5 mm precipitation."""
        hist = self.historical.get(city_key, {})
        precips = hist.get("precipitation_sum", [])
        if not precips:
            return 0.3  # sensible prior
        rainy = sum(1 for p in precips if p is not None and p > 0.5)
        return rainy / len(precips)

    def _temp_exceedance_rate(self, city_key: str, threshold_c: float) -> float:
        """Fraction of historical days where max temp exceeded threshold."""
        hist = self.historical.get(city_key, {})
        temps = hist.get("temp_max", [])
        if not temps:
            return 0.5
        exceed = sum(1 for t in temps if t is not None and t > threshold_c)
        return exceed / len(temps)

    # ── model probability ─────────────────────────────────────────────────────

    def predict(self, market: dict) -> dict:
        """
        Given a parsed market dict (from polymarket_fetcher.parse_market),
        return the market dict enriched with:
            model_prob, edge, recommendation
        """
        city_raw = market.get("matched_city") or ""
        city_key = city_raw.lower()
        summary  = self.summaries.get(city_key, {})

        question = market.get("question", "")
        metric, threshold = _extract_threshold(question)

        market_prob = market.get("yes_prob", 0.5)
        model_prob  = 0.5  # fallback

        # ── Rain ─────────────────────────────────────────────────────────────
        if metric == "rain":
            base_rate    = self._rain_base_rate(city_key)
            forecast_val = summary.get("total_precip_mm", 0.0) or 0.0
            # Sigmoid-based: more rain forecast → higher probability
            p_forecast   = 1 / (1 + math.exp(-0.5 * (forecast_val - 1.0)))
            model_prob   = 0.6 * p_forecast + 0.4 * base_rate

        # ── Temperature above threshold (°C) ─────────────────────────────────
        elif metric == "temp_above_c" and threshold is not None:
            base_rate  = self._temp_exceedance_rate(city_key, threshold)
            forecast_max = summary.get("max_temp_c")
            if forecast_max is not None:
                # If forecast max is well above/below threshold → strong signal
                delta = forecast_max - threshold
                p_forecast = 1 / (1 + math.exp(-delta))
                model_prob = 0.7 * p_forecast + 0.3 * base_rate
            else:
                model_prob = base_rate

        # ── Temperature above threshold (°F) ─────────────────────────────────
        elif metric == "temp_above_f" and threshold is not None:
            threshold_c = _f_to_c(threshold)
            base_rate   = self._temp_exceedance_rate(city_key, threshold_c)
            forecast_max = summary.get("max_temp_c")
            if forecast_max is not None:
                delta = forecast_max - threshold_c
                p_forecast = 1 / (1 + math.exp(-delta))
                model_prob = 0.7 * p_forecast + 0.3 * base_rate
            else:
                model_prob = base_rate

        # ── Wind ─────────────────────────────────────────────────────────────
        elif metric == "wind_above" and threshold is not None:
            forecast_wind = summary.get("max_wind_kmh")
            if forecast_wind is not None:
                delta = forecast_wind - threshold
                model_prob = 1 / (1 + math.exp(-0.3 * delta))
            else:
                model_prob = 0.5

        # ── Unknown / no city ─────────────────────────────────────────────────
        else:
            # No reliable signal → trust the market
            model_prob = market_prob

        # Clip to (0.02, 0.98)
        model_prob = float(np.clip(model_prob, 0.02, 0.98))
        edge       = round(model_prob - market_prob, 4)

        # Recommendation
        abs_edge = abs(edge)
        if abs_edge < 0.03:
            rec = "SKIP"
        elif edge > 0:
            rec = "BUY_YES"
        else:
            rec = "BUY_NO"

        return {
            **market,
            "model_prob": round(model_prob, 4),
            "market_prob": round(market_prob, 4),
            "edge":        edge,
            "abs_edge":    abs_edge,
            "recommendation": rec,
            "metric":      metric,
            "threshold":   threshold,
        }

    def predict_all(self, markets: list[dict]) -> list[dict]:
        results = [self.predict(m) for m in markets]
        results.sort(key=lambda x: x["abs_edge"], reverse=True)
        return results
