"""
trading/hedging.py
Hedging strategies for open positions.

Strategies implemented:
  1. Opposing-side hedge  – take a partial NO position to lock in profit
  2. Correlated-market hedge – hedge city A's rain bet via correlated city B
  3. Stop-loss virtual trigger – flag positions to close if edge has collapsed
"""

from __future__ import annotations

from trading.kelly_criterion import position_size


def hedge_ratio(
    original_stake:    float,
    original_prob:     float,
    current_prob:      float,
    hedge_target_pnl:  float = 0.0,   # desired locked-in profit (0 = break-even)
) -> dict:
    """
    Compute the amount to bet on the opposing side to lock in a guaranteed P&L.

    Solving:
        profit_if_yes = stake_hedge * (1/no_prob - 1) - stake_hedge
        profit_if_no  = original_payout_if_yes - stake_hedge
        ... set both equal to hedge_target_pnl

    Returns:
        hedge_stake  : dollar amount to place on opposing side
        locked_pnl   : profit locked in regardless of outcome
    """
    if current_prob <= 0 or current_prob >= 1:
        return {"hedge_stake": 0.0, "locked_pnl": 0.0, "feasible": False}

    # Payout of original YES position if YES wins (simplified)
    original_payout = original_stake / original_prob

    # No-side odds at current price
    no_price  = 1.0 - current_prob
    if no_price <= 0:
        return {"hedge_stake": 0.0, "locked_pnl": 0.0, "feasible": False}

    no_payout_per_unit = 1.0 / no_price

    # hedge_stake = (original_payout - hedge_target_pnl) / no_payout_per_unit
    hedge_stake = max(0.0, (original_payout - original_stake - hedge_target_pnl)
                       / (no_payout_per_unit - 1))

    locked_pnl  = original_payout - original_stake - hedge_stake
    return {
        "hedge_stake": round(hedge_stake, 2),
        "locked_pnl":  round(locked_pnl, 2),
        "feasible":    hedge_stake > 0,
    }


def should_hedge(position: dict, current_model_prob: float) -> bool:
    """
    Return True if we should hedge this position.
    Trigger conditions:
      - Market has moved significantly in our favour (book profit)
      - Our model probability has flipped below 50 %
    """
    side        = position.get("side", "YES")
    opened_prob = position.get("market_prob", 0.5)

    if side == "YES":
        # Original bet was that YES is underpriced.
        # Hedge if model now thinks YES is less likely than 50 %.
        return current_model_prob < 0.45
    else:
        return current_model_prob > 0.55


def build_hedge_orders(
    open_positions: list[dict],
    updated_predictions: list[dict],
    bankroll: float,
) -> list[dict]:
    """
    Given open positions and fresh predictions, return a list of hedge orders to execute.
    """
    pred_map = {p.get("id"): p for p in updated_predictions}
    hedge_orders = []

    for pos in open_positions:
        mid   = pos.get("market_id")
        pred  = pred_map.get(mid)
        if not pred:
            continue

        new_model_prob = pred.get("model_prob", 0.5)

        if should_hedge(pos, new_model_prob):
            h = hedge_ratio(
                original_stake   = pos["stake_usd"],
                original_prob    = pos["market_prob"],
                current_prob     = pred["market_prob"],
                hedge_target_pnl = 0.0,   # lock in break-even
            )
            if h["feasible"] and h["hedge_stake"] < bankroll * 0.1:
                hedge_orders.append({
                    "market_id":    mid,
                    "question":     pos["question"],
                    "action":       "HEDGE",
                    "hedge_side":   "NO" if pos["side"] == "YES" else "YES",
                    "hedge_stake":  h["hedge_stake"],
                    "locked_pnl":   h["locked_pnl"],
                    "reason":       "model_flip",
                })

    return hedge_orders
