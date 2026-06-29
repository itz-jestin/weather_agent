"""
data/mock_data.py
Realistic mock data used when external APIs are unreachable.
Mirrors the exact schema returned by weather_fetcher and polymarket_fetcher.
"""

from __future__ import annotations

MOCK_WEATHER = [
    {
        "city": "New York", "country": "US",
        "max_temp_c": 31.4, "min_temp_c": 22.1,
        "total_precip_mm": 0.0, "max_wind_kmh": 18.2, "will_rain": False,
    },
    {
        "city": "London", "country": "GB",
        "max_temp_c": 19.8, "min_temp_c": 13.5,
        "total_precip_mm": 2.4, "max_wind_kmh": 24.1, "will_rain": True,
    },
    {
        "city": "Tokyo", "country": "JP",
        "max_temp_c": 34.2, "min_temp_c": 26.8,
        "total_precip_mm": 8.7, "max_wind_kmh": 12.4, "will_rain": True,
    },
    {
        "city": "Dubai", "country": "AE",
        "max_temp_c": 44.1, "min_temp_c": 33.2,
        "total_precip_mm": 0.0, "max_wind_kmh": 22.0, "will_rain": False,
    },
    {
        "city": "Sydney", "country": "AU",
        "max_temp_c": 14.3, "min_temp_c": 9.1,
        "total_precip_mm": 0.8, "max_wind_kmh": 31.5, "will_rain": True,
    },
    {
        "city": "Mumbai", "country": "IN",
        "max_temp_c": 33.0, "min_temp_c": 27.5,
        "total_precip_mm": 22.3, "max_wind_kmh": 41.2, "will_rain": True,
    },
    {
        "city": "Paris", "country": "FR",
        "max_temp_c": 28.7, "min_temp_c": 17.9,
        "total_precip_mm": 0.0, "max_wind_kmh": 15.3, "will_rain": False,
    },
]

MOCK_HISTORICAL = {
    "new york":   {"temp_max": [28,29,31,27,30,32,26,33,29,28]*3, "precipitation_sum": [0,0,2.1,0,0,0,5.3,0,0,1.2]*3},
    "london":     {"temp_max": [17,18,16,19,20,15,14,21,18,17]*3, "precipitation_sum": [1.2,0,3.4,0,2.1,5.5,0,0,1.8,0]*3},
    "tokyo":      {"temp_max": [30,32,33,31,34,29,35,33,31,32]*3, "precipitation_sum": [5.2,0,12.3,8.1,0,0,3.4,0,6.2,0]*3},
    "dubai":      {"temp_max": [42,43,41,44,43,45,42,40,43,44]*3, "precipitation_sum": [0,0,0,0,0,0,0,0,0,0]*3},
    "sydney":     {"temp_max": [13,15,14,16,12,13,15,14,13,16]*3, "precipitation_sum": [0,1.2,0,3.4,0,0,2.1,0,0,1.8]*3},
    "mumbai":     {"temp_max": [32,33,31,34,33,32,33,34,31,32]*3, "precipitation_sum": [15,22,18,30,12,25,8,19,24,11]*3},
    "paris":      {"temp_max": [26,27,28,25,29,27,26,28,25,27]*3, "precipitation_sum": [0,0,1.2,0,0,3.1,0,0,2.4,0]*3},
}

MOCK_MARKETS = [
    {
        "id": "0xabc001",
        "question": "Will it rain in London on June 29, 2026?",
        "category": "weather", "end_date": "2026-06-29",
        "yes_prob": 0.41, "no_prob": 0.59,
        "volume": 8_420, "liquidity": 3_200, "matched_city": "london",
        "url": "https://polymarket.com/event/rain-london-jun29",
    },
    {
        "id": "0xabc002",
        "question": "Will Tokyo temperature exceed 35°C on June 30?",
        "category": "weather", "end_date": "2026-06-30",
        "yes_prob": 0.52, "no_prob": 0.48,
        "volume": 14_200, "liquidity": 6_800, "matched_city": "tokyo",
        "url": "https://polymarket.com/event/tokyo-35c-jun30",
    },
    {
        "id": "0xabc003",
        "question": "Will New York see a high above 90°F on June 29?",
        "category": "weather", "end_date": "2026-06-29",
        "yes_prob": 0.60, "no_prob": 0.40,
        "volume": 22_100, "liquidity": 9_400, "matched_city": "new york",
        "url": "https://polymarket.com/event/ny-90f-jun29",
    },
    {
        "id": "0xabc004",
        "question": "Will it rain in Mumbai on June 29, 2026?",
        "category": "weather", "end_date": "2026-06-29",
        "yes_prob": 0.58, "no_prob": 0.42,
        "volume": 6_300, "liquidity": 2_100, "matched_city": "mumbai",
        "url": "https://polymarket.com/event/rain-mumbai-jun29",
    },
    {
        "id": "0xabc005",
        "question": "Will Dubai temperature exceed 44°C on June 30?",
        "category": "weather", "end_date": "2026-06-30",
        "yes_prob": 0.39, "no_prob": 0.61,
        "volume": 4_800, "liquidity": 1_900, "matched_city": "dubai",
        "url": "https://polymarket.com/event/dubai-44c-jun30",
    },
    {
        "id": "0xabc006",
        "question": "Will Sydney see precipitation on June 29?",
        "category": "weather", "end_date": "2026-06-29",
        "yes_prob": 0.33, "no_prob": 0.67,
        "volume": 3_100, "liquidity": 1_200, "matched_city": "sydney",
        "url": "https://polymarket.com/event/rain-sydney-jun29",
    },
    {
        "id": "0xabc007",
        "question": "Will Paris temperature exceed 30°C on June 29?",
        "category": "weather", "end_date": "2026-06-29",
        "yes_prob": 0.44, "no_prob": 0.56,
        "volume": 9_700, "liquidity": 4_100, "matched_city": "paris",
        "url": "https://polymarket.com/event/paris-30c-jun29",
    },
    {
        "id": "0xabc008",
        "question": "Will wind speed in Tokyo exceed 40 km/h on June 30?",
        "category": "weather", "end_date": "2026-06-30",
        "yes_prob": 0.22, "no_prob": 0.78,
        "volume": 2_800, "liquidity": 1_050, "matched_city": "tokyo",
        "url": "https://polymarket.com/event/tokyo-wind-jun30",
    },
    {
        "id": "0xabc009",
        "question": "Will it rain in New York on June 30, 2026?",
        "category": "weather", "end_date": "2026-06-30",
        "yes_prob": 0.28, "no_prob": 0.72,
        "volume": 11_400, "liquidity": 5_200, "matched_city": "new york",
        "url": "https://polymarket.com/event/rain-ny-jun30",
    },
    {
        "id": "0xabc010",
        "question": "Will London temperature exceed 22°C on June 30?",
        "category": "weather", "end_date": "2026-06-30",
        "yes_prob": 0.36, "no_prob": 0.64,
        "volume": 7_600, "liquidity": 3_300, "matched_city": "london",
        "url": "https://polymarket.com/event/london-22c-jun30",
    },
]
