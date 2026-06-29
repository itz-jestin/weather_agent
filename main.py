"""
main.py  –  Weather Prediction Agent
Entry point for the CrowdWisdomTrading intern assessment.

Usage:
    python main.py                  # run full agent cycle
    python main.py --dashboard      # show dashboard only (no agent)
    python main.py --settle ID YES  # settle a position manually
    python main.py --loop 60        # run every N minutes

Requires .env with:
    OPENROUTER_API_KEY=...
    APIFY_TOKEN=...         (optional – enriches weather data)
"""

from __future__ import annotations

import argparse
import sys
import time

from dotenv import load_dotenv
load_dotenv()  # must happen before config imports

from rich.console import Console

from config import STARTING_BANKROLL
from data.weather_fetcher import fetch_all_cities, fetch_historical
from data.polymarket_fetcher import fetch_parsed_markets
from models.prediction_model import WeatherPredictor
from trading.paper_trader import PaperTrader
from trading.hedging import build_hedge_orders
from agents.trading_agent import build_trading_agent
from ui.dashboard import print_snapshot
from config import CITIES, OPENROUTER_API_KEY


console = Console(force_terminal=True, highlight=False)


def run_manual_cycle() -> None:
    """
    Run one full cycle WITHOUT the LLM agent.
    Useful when OPENROUTER_API_KEY is not set or for quick testing.
    """
    console.print("[bold cyan]▶ Running weather-trading cycle...[/bold cyan]\n")

    # 1. Weather data
    console.print("[yellow]1/5  Fetching weather data...[/yellow]")
    weather = fetch_all_cities()

    # 2. Market data
    console.print("[yellow]2/5  Fetching Polymarket weather markets...[/yellow]")
    markets = fetch_parsed_markets()

    # 3. Historical calibration
    console.print("[yellow]3/5  Loading historical data for calibration...[/yellow]")
    hist = {}
    for city in CITIES:
        h = fetch_historical(city, days_back=30)
        hist[city["name"].lower()] = h

    # 4. Predictions
    console.print("[yellow]4/5  Running prediction model...[/yellow]")
    predictor = WeatherPredictor(weather_summaries=weather, historical_data=hist)
    predictions = predictor.predict_all(markets)
    opps = [p for p in predictions if p["recommendation"] != "SKIP"]
    console.print(f"       → {len(opps)} opportunities found (edge > 3%)")

    # 5. Paper trades
    console.print("[yellow]5/5  Placing paper trades...[/yellow]")
    trader = PaperTrader()
    for pred in opps[:5]:          # cap at 5 trades per cycle
        if pred["abs_edge"] >= 0.05:
            order = trader.place_order(pred)
            if order:
                console.print(
                    f"       ✅  [{order['side']}] {order['question'][:55]}  "
                    f"stake=${order['stake_usd']:.2f}  edge={order['edge']:+.3f}"
                )

    # Hedging
    hedge_orders = build_hedge_orders(
        open_positions      = trader.positions,
        updated_predictions = predictions,
        bankroll            = trader.bankroll,
    )
    if hedge_orders:
        console.print(f"\n[bold red]⚠  {len(hedge_orders)} hedge order(s) recommended[/bold red]")
        for h in hedge_orders:
            console.print(f"   HEDGE {h['hedge_side']} ${h['hedge_stake']:.2f} "
                          f"→ locks in ${h['locked_pnl']:.2f}  ({h['reason']})")

    # Dashboard
    print_snapshot(
        weather   = weather,
        markets   = [p for p in predictions[:20]],
        positions = trader.positions,
        history   = trader.history,
        stats     = trader.stats(),
    )


def run_agent_cycle() -> None:
    """
    Run one full cycle via the HermesAgent (LLM-driven).
    Falls back to manual cycle automatically if the LLM API fails.
    """
    console.print("[bold cyan]▶ Launching Hermes Agent cycle...[/bold cyan]\n")
    agent = build_trading_agent()
    goal  = (
        "Run a complete trading cycle:\n"
        "1. Fetch weather data for all cities.\n"
        "2. Fetch open weather markets from Polymarket.\n"
        "3. Run predictions to find edges.\n"
        "4. Place up to 5 paper trades (min edge 5%).\n"
        "5. Check if any open positions need hedging.\n"
        "6. Report portfolio status with key statistics."
    )
    try:
        result = agent.run(goal)
    except Exception as exc:
        console.print(f"[bold red]Agent error: {exc}[/bold red]")
        console.print("[yellow]→ Falling back to manual cycle...[/yellow]\n")
        run_manual_cycle()
        return
    console.print("\n[bold green]Agent final response:[/bold green]")
    console.print(result)

    # Show dashboard with current state
    from agents.trading_agent import (
        _weather_cache, _market_cache, _predictor, _trader
    )
    if _weather_cache or _market_cache:
        markets = _predictor.predict_all(_market_cache) if _predictor and _market_cache else []
        print_snapshot(
            weather   = _weather_cache,
            markets   = markets,
            positions = _trader.positions,
            history   = _trader.history,
            stats     = _trader.stats(),
            agent_log = result,
        )


def show_dashboard_only() -> None:
    """Show the dashboard with current ledger data."""
    trader = PaperTrader()
    print_snapshot(
        weather   = [],
        markets   = [],
        positions = trader.positions,
        history   = trader.history,
        stats     = trader.stats(),
    )


def settle_position(market_id: str, outcome: str) -> None:
    trader = PaperTrader()
    result = trader.settle(market_id, outcome.upper())
    if result:
        pnl_color = "green" if result["pnl_usd"] >= 0 else "red"
        console.print(
            f"[bold]Settled:[/bold] {result['question'][:60]}\n"
            f"  Outcome: {result['outcome']}  |  "
            f"P&L: [{pnl_color}]${result['pnl_usd']:+.2f}[/{pnl_color}]  |  "
            f"Bankroll: ${trader.bankroll:.2f}"
        )
    else:
        console.print(f"[red]No open position found for market_id={market_id}[/red]")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Weather Prediction Trading Agent")
    parser.add_argument("--dashboard", action="store_true",
                        help="Show dashboard only (no trading cycle)")
    parser.add_argument("--manual", action="store_true",
                        help="Run without LLM agent (manual cycle)")
    parser.add_argument("--settle", nargs=2, metavar=("MARKET_ID", "OUTCOME"),
                        help="Settle a position: --settle <id> YES|NO")
    parser.add_argument("--agent", action="store_true",
                        help="Use LLM agent (requires OpenRouter key + tool-calling model)")
    parser.add_argument("--loop", type=int, default=0,
                        help="Repeat cycle every N minutes (0 = run once)")
    args = parser.parse_args()

    if args.settle:
        settle_position(args.settle[0], args.settle[1])
        return

    if args.dashboard:
        show_dashboard_only()
        return

    # Default to manual cycle (works without LLM tool-calling support)
    # Use --agent flag to explicitly run the LLM agent
    if getattr(args, 'agent', False) and OPENROUTER_API_KEY:
        cycle_fn = run_agent_cycle
    else:
        cycle_fn = run_manual_cycle

    if args.loop > 0:
        console.print(f"[bold]Looping every {args.loop} minutes. Press Ctrl+C to stop.[/bold]")
        while True:
            try:
                cycle_fn()
                console.print(f"\n[dim]Next cycle in {args.loop}m…[/dim]")
                time.sleep(args.loop * 60)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped.[/yellow]")
                break
    else:
        cycle_fn()


if __name__ == "__main__":
    main()
# ── Demo mode (run when APIs are blocked / offline) ───────────────────────────

def run_demo_cycle() -> None:
    """
    Full pipeline run using bundled mock data.
    Identical logic to run_manual_cycle – just skips live API calls.
    """
    from data.mock_data import MOCK_WEATHER, MOCK_HISTORICAL, MOCK_MARKETS
    from models.prediction_model import WeatherPredictor
    from trading.paper_trader import PaperTrader
    from trading.hedging import build_hedge_orders

    console.print("[bold cyan]▶ Running DEMO cycle (mock data)...[/bold cyan]\n")

    weather  = MOCK_WEATHER
    markets  = MOCK_MARKETS
    hist     = MOCK_HISTORICAL

    console.print("[yellow]  Building prediction model...[/yellow]")
    predictor = WeatherPredictor(weather_summaries=weather, historical_data=hist)
    predictions = predictor.predict_all(markets)

    trader = PaperTrader()
    opps   = [p for p in predictions if p["recommendation"] != "SKIP"]
    console.print(f"  → {len(opps)} opportunities with edge > 3%")

    for pred in opps[:5]:
        if pred["abs_edge"] >= 0.05:
            order = trader.place_order(pred)
            if order:
                console.print(
                    f"  ✅  [{order['side']}] {order['question'][:55]}  "
                    f"stake=${order['stake_usd']:.2f}  edge={order['edge']:+.3f}"
                )

    hedges = build_hedge_orders(trader.positions, predictions, trader.bankroll)
    if hedges:
        console.print(f"\n[bold red]⚠  {len(hedges)} hedge(s) recommended[/bold red]")
        for h in hedges:
            console.print(f"   HEDGE {h['hedge_side']} ${h['hedge_stake']:.2f} → "
                          f"locks ${h['locked_pnl']:.2f}  ({h['reason']})")

    print_snapshot(
        weather   = weather,
        markets   = predictions,
        positions = trader.positions,
        history   = trader.history,
        stats     = trader.stats(),
    )
