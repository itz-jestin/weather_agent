"""
trading/paper_trader.py
In-memory paper trading engine.
Tracks positions, bankroll, P&L, and trade history.
"""

from __future__ import annotations

import datetime
import json
import os
from typing import Any

from config import STARTING_BANKROLL
from trading.kelly_criterion import position_size


LEDGER_FILE = "paper_ledger.json"


class PaperTrader:
    def __init__(self, starting_bankroll: float = STARTING_BANKROLL):
        self.bankroll: float = starting_bankroll
        self.starting: float = starting_bankroll
        self.positions: list[dict] = []    # open positions
        self.history:   list[dict] = []    # closed trades
        self._load()

    # ── persistence ───────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(LEDGER_FILE):
            try:
                with open(LEDGER_FILE) as f:
                    data = json.load(f)
                self.bankroll  = data.get("bankroll",  self.starting)
                self.positions = data.get("positions", [])
                self.history   = data.get("history",   [])
                print(f"[paper_trader] Ledger loaded – bankroll ${self.bankroll:.2f}")
            except Exception:
                pass

    def _save(self):
        with open(LEDGER_FILE, "w") as f:
            json.dump({
                "bankroll":  self.bankroll,
                "positions": self.positions,
                "history":   self.history,
            }, f, indent=2)

    # ── placing orders ────────────────────────────────────────────────────────

    def place_order(self, prediction: dict, fractional_kelly: float = 0.5) -> dict | None:
        """
        Evaluate a prediction and place a paper trade if there is positive edge.

        Args:
            prediction : output of WeatherPredictor.predict()
            fractional_kelly : Kelly multiplier (default 0.5)

        Returns the order dict, or None if no bet is placed.
        """
        rec        = prediction.get("recommendation", "SKIP")
        market_id  = prediction.get("id", "unknown")
        question   = prediction.get("question", "")
        model_prob = prediction.get("model_prob", 0.5)
        mkt_prob   = prediction.get("market_prob", 0.5)

        if rec == "SKIP":
            return None

        side = "YES" if rec == "BUY_YES" else "NO"

        sizing = position_size(
            bankroll    = self.bankroll,
            model_prob  = model_prob,
            market_prob = mkt_prob,
            side        = side,
            fractional  = fractional_kelly,
        )

        if sizing["stake_usd"] < 0.01:
            return None

        # Check if we already have an open position on this market
        existing = next((p for p in self.positions if p["market_id"] == market_id), None)
        if existing:
            return None   # don't double-up

        # Deduct stake from bankroll
        self.bankroll = round(self.bankroll - sizing["stake_usd"], 2)

        order = {
            "market_id":   market_id,
            "question":    question,
            "city":        prediction.get("matched_city", "unknown"),
            "side":        side,
            "stake_usd":   sizing["stake_usd"],
            "kelly_frac":  sizing["kelly_fraction"],
            "model_prob":  model_prob,
            "market_prob": mkt_prob,
            "edge":        prediction.get("edge", 0),
            "ev":          sizing["expected_value"],
            "end_date":    prediction.get("end_date", ""),
            "opened_at":   datetime.datetime.utcnow().isoformat(),
            "status":      "OPEN",
        }

        self.positions.append(order)
        self._save()
        return order

    # ── settling positions ────────────────────────────────────────────────────

    def settle(self, market_id: str, outcome: str) -> dict | None:
        """
        Settle an open position.
        outcome = "YES" or "NO"
        """
        pos = next((p for p in self.positions if p["market_id"] == market_id), None)
        if not pos:
            return None

        won = pos["side"] == outcome
        # Simple binary market: win returns stake / market_prob
        if won:
            payout = pos["stake_usd"] / (pos["market_prob"] if pos["side"] == "YES"
                                         else 1 - pos["market_prob"])
        else:
            payout = 0.0

        pnl = round(payout - pos["stake_usd"], 2)
        self.bankroll = round(self.bankroll + payout, 2)

        result = {
            **pos,
            "outcome":      outcome,
            "won":          won,
            "payout_usd":   round(payout, 2),
            "pnl_usd":      pnl,
            "settled_at":   datetime.datetime.utcnow().isoformat(),
            "status":       "SETTLED",
        }

        self.positions = [p for p in self.positions if p["market_id"] != market_id]
        self.history.append(result)
        self._save()
        return result

    # ── stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        total_pnl = sum(t["pnl_usd"] for t in self.history)
        wins = sum(1 for t in self.history if t.get("won"))
        total_trades = len(self.history)
        win_rate = (wins / total_trades) if total_trades else 0.0
    
        open_staked = sum(p["stake_usd"] for p in self.positions)
        closed_staked = sum(t["stake_usd"] for t in self.history)
        total_staked = open_staked + closed_staked
    
        portfolio_value = self.bankroll + open_staked
        cash = self.bankroll
        open_value = sum(p["stake_usd"] for p in self.positions)
        portfolio_value = cash + open_value
        
        roi = (
            (portfolio_value - self.starting)
            / self.starting
            * 100
        )
    
        return {
            "cash": round(cash, 2),
            "portfolio_value": round(portfolio_value, 2),
            "starting": round(self.starting, 2),
            "unrealized_value": round(open_value, 2),
            "realized_pnl": round(total_pnl, 2),
            "roi_pct": round(roi, 2),
            "total_staked": round(total_staked, 2),
            "open_positions": len(self.positions),
            "closed_trades": total_trades,
            "win_rate": round(win_rate * 100, 1),
        }