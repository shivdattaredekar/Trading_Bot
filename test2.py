import os
import pandas as pd
import numpy as np
from fyers_apiv3.fyersModel import FyersModel
from datetime import datetime, timedelta

# ------------------------------
# CONFIG
# ------------------------------
CLIENT_ID = "MX3ZI638YI-100"
ACCESS_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCcEdGa05vRlgxMTFlUDRQLVVsVDFld3BlbmozdXV5R0pEMmVSeV9Ha01sWS1qMmNXeU1CTy0xdzZoYjhtU3NyTzBUNzJWb2tyUlNvT1ZtQTBBRmpzM04xWUFZNUJrR01MYTRfNWQ5b2hoX096OVJDZz0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiIyZmJlNGZmZTZiMGJlZDRjMThlM2ZiMDhkYzJiZmRjMDYzMWY2NGVkMDgyNTk2NWM4Yjc3Y2JkOCIsImlzRGRwaUVuYWJsZWQiOiJZIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiWFIwNDc1MCIsImFwcFR5cGUiOjEwMCwiZXhwIjoxNzYzMjUzMDAwLCJpYXQiOjE3NjMyMDMzNDEsImlzcyI6ImFwaS5meWVycy5pbiIsIm5iZiI6MTc2MzIwMzM0MSwic3ViIjoiYWNjZXNzX3Rva2VuIn0.LimJBMwnjkSZwpC_p1mwUHgnp9IfJe3kEUr4c-SeIFc'

SYMBOL = "NSE:BPCL-EQ"
TIMEFRAME = "5"    # 5-minute candles


RR = 3

DATE_FROM = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
DATE_TO = datetime.now().strftime("%Y-%m-%d")


fyers = FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN)


# ------------------------------
# FETCH CANDLES
# ------------------------------
def get_candles():
    data = fyers.history({
        "symbol": SYMBOL,
        "resolution": "5",
        "date_format": "1",
        "range_from": DATE_FROM,
        "range_to": DATE_TO,
        "cont_flag": "1"
    })

    raw = data.get("candles", [])

    candles = []
    for c in raw:
        candles.append({
            "timestamp": datetime.fromtimestamp(c[0]).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "open": c[1],
            "high": c[2],
            "low": c[3],
            "close": c[4],
            "volume": c[5]
        })

    return candles


# ------------------------------
# CALCULATE EMA-5
# ------------------------------
def calculate_ema(candles, period=5):
    closes = [c["close"] for c in candles]
    timestamps = [c["timestamp"] for c in candles]

    if len(closes) < period:
        return {}

    ema_values = {}
    multiplier = 2 / (period + 1)

    sma = sum(closes[:period]) / period
    ema_values[timestamps[period - 1]] = sma
    prev_ema = sma

    for i in range(period, len(closes)):
        price = closes[i]
        ts = timestamps[i]
        ema = (price - prev_ema) * multiplier + prev_ema
        ema_values[ts] = ema
        prev_ema = ema

    return ema_values


# ------------------------------
# EVALUATE SIGNALS (UPDATED LOGIC)
# ------------------------------
def get_visual_signals(candles, ema):
    signals = []

    for i in range(1, len(candles)):
        A = candles[i - 1]  # previous candle
        B = candles[i]      # current candle

        tsA = A["timestamp"]
        tsB = B["timestamp"]

        # EMA must exist for Candle A
        if tsA not in ema:
            continue

        emaA = ema[tsA]

        # ----------- UPDATED LOGIC -----------

        cond1 = A["close"] > emaA      # Close above EMA
        cond2 = A["low"] > emaA        # Low never touched EMA  <-- NEW RULE
        cond3 = B["low"] < A["low"]    # Break of previous low

        if cond1 and cond2 and cond3:
            entry = A["low"]
            sl = A["high"]
            target = entry - RR * (sl - entry)

            signals.append({
                "timestamp": tsB,
                "entry_price": entry,
                "stop_loss": sl,
                "target": target
            })

    return signals


# ------------------------------
# MAIN
# ------------------------------
candles = get_candles()
ema = calculate_ema(candles)
signals = get_visual_signals(candles, ema)

print(f"\nTotal signals found: {len(signals)}\n")

# for s in signals:
#     print(f"{s['timestamp']} | Entry: {s['entry_price']} | SL: {s['stop_loss']} | Target: {s['target']}")

# print(candles)

import csv

# candles must be a list of dicts like:
# [
#   {"timestamp": "...", "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0},
#   ...
# ]

# Ensure candles list is not empty
if len(candles) == 0:
    raise ValueError("No candles found to export.")

# Export to CSV
csv_filename = "candles.csv"

with open(csv_filename, "w", newline='') as f:
    writer = csv.DictWriter(f, fieldnames=candles[0].keys())
    writer.writeheader()
    writer.writerows(candles)

print(f"\nFile saved successfully: {csv_filename}")


