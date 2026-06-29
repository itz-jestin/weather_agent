"""
trading/kelly_criterion.py
Kelly Criterion position sizing for binary prediction markets.

For a binary market where:
  p  = our estimated probability of YES
  b  = net odds on a YES bet  (1/yes_price - 1)

Full Kelly fraction: f* = (p*b - (1-p)) / b
We apply a fractional Kelly for safety (configurable).
"""

from __future__ import annotations

from config import MAX_KELLY_FRACTION


def kelly_fraction(
    model_prob: float,
    market_prob: float,
    fractional: float = 0.5,
) -> float:
    """
    Compute Kelly-optimal fraction of bankroll to bet on YES.

    Args:
        model_prob  : our estimate of P(YES)
        market_prob : implied probability from the market (= market price)
        fractional  : fraction of full Kelly to use (0.5 = "half Kelly")

    Returns:
        Fraction of bankroll to stake (0.0 if no edge or negative edge).
    """
    p = model_prob
    q = 1.0 - p

    if market_prob <= 0 or market_prob >= 1:
        return 0.0

    # Net odds per unit staked on YES
    b = (1.0 / market_prob) - 1.0

    full_kelly = (p * b - q) / b
    if full_kelly <= 0:
        return 0.0

    # Apply fractional Kelly and cap at MAX_KELLY_FRACTION
    return min(full_kelly * fractional, MAX_KELLY_FRACTION)


def kelly_no(
    model_prob: float,
    market_prob_yes: float,
    fractional: float = 0.5,
) -> float:
    """
    Compute Kelly-optimal fraction for betting NO.
    """
    # NO bet: market prob of YES is (1 - market_prob_no)
    market_prob_no = 1.0 - market_prob_yes
    model_prob_no  = 1.0 - model_prob
    return kelly_fraction(model_prob_no, market_prob_no, fractional)


def position_size(
    bankroll:    float,
    model_prob:  float,
    market_prob: float,
    side:        str = "YES",    # "YES" or "NO"
    fractional:  float = 0.5,
) -> dict:
    """
    Full sizing decision.

    Returns a dict with:
        side, fraction, stake_usd, expected_value, expected_profit_usd
    """
    if side == "YES":
        frac = kelly_fraction(model_prob, market_prob, fractional)
    else:
        frac = kelly_no(model_prob, market_prob, fractional)
    
    # Safety cap: never risk more than 25% of bankroll
    frac = max(0.0, min(frac, 0.25))
    stake = bankroll * frac
    odds      = (1.0 / market_prob) - 1.0 if side == "YES" else (1.0 / (1 - market_prob)) - 1.0
    ev        = round(frac * odds * (model_prob if side == "YES" else 1 - model_prob)
                      - frac * (1 - model_prob if side == "YES" else model_prob), 6)
    exp_profit = round(stake * ev / frac if frac else 0.0, 2)

    return {
        "side":             side,
        "kelly_fraction":   round(frac, 4),
        "stake_usd":        round(stake,2),
        "expected_value":   round(ev, 4),
        "expected_profit":  exp_profit,
    }
