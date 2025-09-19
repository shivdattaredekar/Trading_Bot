# strategies/ema_strategy.py
from datetime import datetime

from tradingsetup.config.settings import (
    EMA_PERIOD,
    ORDER_QUANTITY,
    SIMULATE,
    MAX_TRADES,
    CAPITAL
)
from tradingsetup.utlis.logger import log
from tradingsetup.login.auth import get_fyers_instance


def get_5min_candles(fyers, symbol):
    data = fyers.history({
        "symbol": symbol,
        "resolution": "5",
        "date_format": "1",
        "range_from": "2025-07-26",
        "range_to": "2025-07-26",
        "cont_flag": "1"
    })
    return data.get("candles", [])

def calculate_ema(prices, period):
    weights = [2 / (period + 1) ** i for i in range(period)][::-1]
    ema = sum(p * w for p, w in zip(prices[-period:], weights)) / sum(weights)
    return ema

def evaluate_entry_and_trade(symbol):
    fyers = get_fyers_instance()
    candles = get_5min_candles(fyers, symbol)

    if len(candles) < EMA_PERIOD + 2:
        return

    prices = [c[4] for c in candles]  # closing prices
    lows = [c[3] for c in candles]
    highs = [c[2] for c in candles]

    for i in range(EMA_PERIOD, len(prices) - 1):
        ema = calculate_ema(prices[:i], EMA_PERIOD)
        if candles[i+1][3] < candles[i][3] and candles[i+1][1] > ema:
            price = candles[i+1][1]
            sl = highs[i]
            target = price - 3 * (price - sl)
            place_trade(symbol, price, sl, target)
            break

def place_trade(symbol, price, sl, target, CAPITAL):
    print(f"[TRADE] {symbol} - Entry: {price:.2f}, SL: {sl:.2f}, Target: {target:.2f}")
    log(symbol, price, sl, target, "SIMULATED" if SIMULATE else "LIVE")

    if not SIMULATE:
        fyers = get_fyers_instance()
        order_data = {
            "symbol": symbol,
            "qty": ORDER_QUANTITY,
            "type": 2,
            "side": -1,
            "productType": "INTRADAY",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": "False",
            "stopLoss": abs(price - sl),
            "takeProfit": abs(price - target)
        }
        response = fyers.place_order(order_data)
        print(response)
