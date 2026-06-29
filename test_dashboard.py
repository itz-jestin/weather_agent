from ui.dashboard import print_snapshot

weather = [
    {
        "city": "Mumbai",
        "max_temp_c": 31,
        "min_temp_c": 26,
        "total_precip_mm": 12,
        "max_wind_kmh": 18,
        "will_rain": True,
    }
]

markets = [
    {
        "question": "Will it rain in Mumbai today?",
        "matched_city": "Mumbai",
        "market_prob": 0.62,
        "model_prob": 0.81,
        "edge": 0.19,
        "recommendation": "BUY_YES",
        "volume": 15000,
    }
]

positions = [
    {
        "question": "Will it rain in Mumbai today?",
        "city": "Mumbai",
        "side": "YES",
        "stake_usd": 25,
        "kelly_frac": 0.12,
        "edge": 0.19,
    }
]

history = []

stats = {
    "bankroll": 975,
    "starting": 1000,
    "roi_pct": -2.5,
    "total_pnl": -25,
    "total_staked": 25,
    "open_positions": 1,
    "closed_trades": 0,
    "win_rate": 0,
}

print_snapshot(weather, markets, positions, history, stats)