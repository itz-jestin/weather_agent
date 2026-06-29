"""
config.py  –  Central configuration for the Weather Prediction Agent
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Look for .env in this file's directory AND the cwd
_here = Path(__file__).parent
load_dotenv(_here / ".env")
load_dotenv(".env")

# ── LLM (OpenRouter) ─────────────────────────────────────────────────────────
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
# Any free model on OpenRouter; swap as desired
LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b:free")

# ── Apify ─────────────────────────────────────────────────────────────────────
APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")

# ── Polymarket ────────────────────────────────────────────────────────────────
POLYMARKET_GAMMA_URL: str = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL: str  = "https://clob.polymarket.com"

# ── Paper-trading defaults ────────────────────────────────────────────────────
STARTING_BANKROLL: float  = 1_000.0   # USD (paper)
MAX_KELLY_FRACTION: float = 0.25       # never bet more than 25 % of bankroll

# ── Cities to track (≥ 5 required) ───────────────────────────────────────────
CITIES: list[dict] = [
    {"name": "New York",   "lat": 40.7128,  "lon": -74.0060, "country": "US"},
    {"name": "London",     "lat": 51.5074,  "lon": -0.1278,  "country": "GB"},
    {"name": "Tokyo",      "lat": 35.6762,  "lon": 139.6503, "country": "JP"},
    {"name": "Dubai",      "lat": 25.2048,  "lon": 55.2708,  "country": "AE"},
    {"name": "Sydney",     "lat": -33.8688, "lon": 151.2093, "country": "AU"},
    {"name": "Mumbai",     "lat": 19.0760,  "lon": 72.8777,  "country": "IN"},
    {"name": "Paris",      "lat": 48.8566,  "lon": 2.3522,   "country": "FR"},
]

# ── Startup diagnostics ───────────────────────────────────────────────────────
if not OPENROUTER_API_KEY:
    print("[config] WARNING: OPENROUTER_API_KEY is not set. "
          "Run with --manual to skip the LLM agent.")
else:
    print(f"[config] OpenRouter key loaded: {OPENROUTER_API_KEY[:12]}...")
