# AI Weather Prediction Trading Agent

## Overview

This project predicts weather events using live weather data and compares them with prediction market probabilities.

The system:

- Fetches live weather data
- Predicts probabilities
- Finds trading opportunities
- Uses Kelly Criterion
- Executes paper trades
- Tracks portfolio performance

## Features

- Live weather collection
- Historical calibration
- Prediction model
- Kelly Criterion
- Paper trading
- Portfolio dashboard
- Automatic fallback when Polymarket API is unavailable

## Installation

```bash
pip install -r requirements.txt
```

Run:

```bash
python main.py
```