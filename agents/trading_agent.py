"""
agents/trading_agent.py
Defines the full set of tools and wires them to the HermesAgent.
"""

from __future__ import annotations

import json
from typing import Any

from agents.hermes_agent import HermesAgent, Tool
from data.weather_fetcher import fetch_all_cities, fetch_historical
from data.polymarket_fetcher import fetch_parsed_markets
from models.prediction_model import WeatherPredictor
from trading.kelly_criterion import position_size
from trading.paper_trader import PaperTrader
from trading.hedging import build_hedge_orders
from config import CITIES


# ── Shared state (in-memory for the session) ─────────────────────────────────

_trader    = PaperTrader()
_predictor: WeatherPredictor | None = None
_weather_cache: list[dict] = []
_market_cache:  list[dict] = []


# ── Tool implementations ──────────────────────────────────────────────────────

def tool_fetch_weather(cities: list[str] | None = None) -> dict:
    global _weather_cache
    print("  [tool] fetch_weather ...")
    _weather_cache = fetch_all_cities()
    return {
        "status": "ok",
        "count":  len(_weather_cache),
        "data":   _weather_cache,
    }


def tool_fetch_markets(limit: int = 50) -> dict:
    global _market_cache
    print("  [tool] fetch_markets ...")
    _market_cache = fetch_parsed_markets()[:limit]
    return {
        "status": "ok",
        "count":  len(_market_cache),
        "markets": _market_cache,
    }


def tool_run_predictions() -> dict:
    global _predictor
    if not _weather_cache:
        return {"error": "No weather data loaded. Call fetch_weather first."}
    if not _market_cache:
        return {"error": "No market data loaded. Call fetch_markets first."}

    # Build historical data for calibration
    hist = {}
    for city in CITIES:
        h = fetch_historical(city, days_back=30)
        hist[city["name"].lower()] = h

    _predictor = WeatherPredictor(
        weather_summaries = _weather_cache,
        historical_data   = hist,
    )
    predictions = _predictor.predict_all(_market_cache)
    opportunities = [p for p in predictions if p["recommendation"] != "SKIP"]
    return {
        "status":        "ok",
        "total_markets": len(predictions),
        "opportunities": len(opportunities),
        "top_10":        opportunities[:10],
    }


def tool_place_trades(max_trades: int = 5, min_edge: float = 0.05) -> dict:
    if _predictor is None:
        return {"error": "Run predictions first."}

    predictions = _predictor.predict_all(_market_cache)
    opportunities = [
        p for p in predictions
        if p["recommendation"] != "SKIP" and p["abs_edge"] >= min_edge
    ]

    placed = []
    for pred in opportunities[:max_trades]:
        order = _trader.place_order(pred)
        if order:
            placed.append(order)
            print(f"  [trade] PLACED {order['side']} on {order['question'][:60]}  "
                  f"stake=${order['stake_usd']:.2f}")

    return {
        "status":          "ok",
        "trades_placed":   len(placed),
        "orders":          placed,
        "bankroll_after":  _trader.bankroll,
    }


def tool_check_hedges() -> dict:
    if _predictor is None or not _market_cache:
        return {"error": "Run predictions first."}

    predictions  = _predictor.predict_all(_market_cache)
    hedge_orders = build_hedge_orders(
        open_positions      = _trader.positions,
        updated_predictions = predictions,
        bankroll            = _trader.bankroll,
    )
    return {
        "status":        "ok",
        "hedge_orders":  hedge_orders,
        "count":         len(hedge_orders),
    }


def tool_portfolio_status() -> dict:
    stats = _trader.stats()
    return {
        **stats,
        "open_positions":  _trader.positions,
        "recent_trades":   _trader.history[-5:],
    }


def tool_settle_position(market_id: str, outcome: str) -> dict:
    result = _trader.settle(market_id, outcome)
    if result:
        return {"status": "settled", "result": result}
    return {"status": "error", "message": f"No open position for {market_id}"}


# ── Build the agent ───────────────────────────────────────────────────────────

def build_trading_agent() -> HermesAgent:
    tools = [
        Tool(
            name="fetch_weather",
            description="Fetch current weather data for all tracked cities from "
                        "Open-Meteo and Apify sources.",
            parameters={
                "type": "object",
                "properties": {
                    "cities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional subset of city names to fetch",
                    }
                },
                "required": [],
            },
            fn=tool_fetch_weather,
        ),
        Tool(
            name="fetch_markets",
            description="Fetch open weather-related prediction markets from Polymarket.",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max markets to fetch (default 50)",
                    }
                },
                "required": [],
            },
            fn=tool_fetch_markets,
        ),
        Tool(
            name="run_predictions",
            description="Run the weather prediction model across all markets. "
                        "Returns top opportunities with edge estimates.",
            parameters={"type": "object", "properties": {}, "required": []},
            fn=tool_run_predictions,
        ),
        Tool(
            name="place_trades",
            description="Place Kelly-sized paper trades on markets with positive edge.",
            parameters={
                "type": "object",
                "properties": {
                    "max_trades": {
                        "type": "integer",
                        "description": "Maximum number of trades to place",
                    },
                    "min_edge": {
                        "type": "number",
                        "description": "Minimum edge required to trade (default 0.05)",
                    },
                },
                "required": [],
            },
            fn=tool_place_trades,
        ),
        Tool(
            name="check_hedges",
            description="Check open positions and generate hedge orders for positions "
                        "where the model probability has changed significantly.",
            parameters={"type": "object", "properties": {}, "required": []},
            fn=tool_check_hedges,
        ),
        Tool(
            name="portfolio_status",
            description="Get current portfolio status: bankroll, open positions, "
                        "P&L, and recent trade history.",
            parameters={"type": "object", "properties": {}, "required": []},
            fn=tool_portfolio_status,
        ),
        Tool(
            name="settle_position",
            description="Settle a closed market and record the P&L.",
            parameters={
                "type": "object",
                "properties": {
                    "market_id": {"type": "string", "description": "Market condition ID"},
                    "outcome":   {"type": "string", "enum": ["YES", "NO"]},
                },
                "required": ["market_id", "outcome"],
            },
            fn=tool_settle_position,
        ),
    ]

    return HermesAgent(tools=tools)
