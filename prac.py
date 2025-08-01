# prac.py
from .stock_filter.filter_logic import *

from fyers_apiv3 import fyersModel
import os
from .config.settings import *
from .utlis.logger import log
import time
from datetime import datetime, timedelta
import statistics
from .trade_logic.ema_strategy import *



def get_fyers_instance():
    access_token = FYERS_ACCESS_TOKEN  # Assume you've completed auth and stored this
    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=access_token, log_path=None)
    log("Authenticated Fyers instance created.")
    return fyers

fyers = get_fyers_instance()


def place_trade(symbol, price, sl, target, timestamp):
    log(f"[TRADE] {symbol} - Entry: {price:.2f}, SL: {sl:.2f}, Target: {target:.2f}")


    try:

        # Check if the current time is within the trading window
        trade_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M')
        trade_delta = abs(datetime.now() - trade_time)
        
        if trade_delta > timedelta(minutes=5):
            log(f"Trade for {symbol} at {timestamp} is outside the trading window. as current time is {datetime.now().time()} hence Skipping.")
            return

        # Place the trade using Fyers API
        log(f"Placing trade for {symbol} at price {price} with SL {sl} and Target {target}.")
        fyers = get_fyers_instance()
        
        # Prepare order data
        order_data = {
            "symbol": symbol,
            "qty": 1,
            "type": 2,  # Market order
            "side": -1,  # Sell
            "productType": "BO",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
            "stopLoss": abs(price - sl),
            "takeProfit": abs(price -target)
        }
        
        
        try:
            response = fyers.place_order(order_data)
            return response
            log(f"Trade placed successfully for {symbol}")
        except Exception as e:
            log(f"Error placing trade for {symbol}: {e}")
            return
        

    except Exception as e:
        log(f"Error placing trade for {symbol}: {e}")
        return

# Example usage of the trading logic
place_trade('NSE:CHAMBLFERT-EQ', 537.55, 549.8, 500.8, '2025-08-01 09:25')


"""
from .trade_logic.ema_strategy import *

stock = ["NSE:WAAREEENER-EQ", "NSE:GODIGIT-EQ", "NSE:PNCINFRA-EQ"]

def get_5min_candles(fyers, symbol):
    data = fyers.history({
        "symbol": symbol,
        "resolution": "5",
        "date_format": "1",
        "range_from": "2025-07-28",
        "range_to": "2025-07-29",
        "cont_flag": "1"
    })
    candles = data.get("candles", [])
    
    # Optional: Convert timestamp to readable format for inspection
    readable_candles = [
        {   "day_time": datetime.fromtimestamp(c[0]).strftime("%Y-%m-%d %H:%M"),
            "open": c[1],
            "high": c[2],
            "low": c[3],
            "close": c[4],
            "volume": c[5]
        }
        for c in candles
    ]
    
    return readable_candles

candles = get_5min_candles(fyers, 'NSE:WAAREEENER-EQ')

#print(candles)

def get_prices(candles):
    price = {}
    for candle in candles:
        day_time = candle["day_time"]
        open_price = candle["open"]
        high = candle["high"]
        low = candle["low"]
        close = candle["close"]
        volume = candle["volume"]
        price[day_time] = close
    return price

print(get_prices(candles))

##print("Calculating EMA...")

# Calculate EMA
def calculate_ema_series(prices_dict, period):
    timestamps = list(prices_dict.keys())
    prices = list(prices_dict.values())
    
    ema_values = {}
    multiplier = 2 / (period + 1)
    sma = sum(prices[:period]) / period
    ema_values[timestamps[period - 1]] = sma

    prev_ema = sma
    for i in range(period, len(prices)):
        current_price = prices[i]
        current_time = timestamps[i]
        ema = (current_price - prev_ema) * multiplier + prev_ema
        ema_values[current_time] = ema
        prev_ema = ema
    
    return ema_values

ema = calculate_ema_series(get_prices(candles), 5)
print(f"EMA: {ema}")


def evaluate_trade_signal(candles, ema):
    signals = []
    for i in range(1, len(candles)):
        current = candles[i]
        prev = candles[i - 1]
        ts = current["day_time"]
        
        # Only evaluate if EMA is available
        if ts not in ema:
            continue
        
        prev_low = prev["low"]
        current_low = current["low"]
        current_close = current["close"]
        current_ema = ema[ts]

        # Check if both candles are above EMA and current candle broke previous low
        if prev_low > current_ema and current_low < prev_low and current_close > current_ema:
            signals.append({
                "timestamp": ts,
                "action": "SELL",
                "entry_price": prev_low,
                "stop_loss": prev["high"],
                "target": prev_low - 3 * (prev["high"] - prev_low)
            })

    return signals

signals = evaluate_trade_signal(candles, ema)

print(signals)
"""

"""
# Fetching stocks from the index
stocks = get_index_symbols()

print(stocks[0])

print('Quotes Data:')

data = {"symbols":"NSE:SBIN-EQ"}
print(fyers.quotes(data))





data = {"symbols":stocks[3]}
data = fyers.quotes(data)
print(data)


print()
quote = data["d"][0]
print(quote)

print()

v = quote["v"]
open_price = v["open_price"]
prev_close = v["prev_close_price"]
volume = v["volume"]
"""

"""
def is_gap_up(fyers, symbol):
    try:
        data = fyers.quotes({"symbols": symbol})
        quote = data["d"][0]["v"]
        open_price = quote["open_price"]
        prev_close = quote["prev_close_price"]
        gap_percent = ((open_price - prev_close) / prev_close) * 100
        return gap_percent 
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return False

def get_avg_volume(fyers, symbol: str, days: int = 60) -> int:
    
    
    
    try:
        # Compute date range
        to_date = int(time.time())
        from_date = int((datetime.now() - timedelta(days=days)).timestamp())

        # Create payload
        data = {
            "symbol": symbol,
            "resolution": "D",
            "date_format": "0",
            "range_from": str(from_date),
            "range_to": str(to_date),
            "cont_flag": "1"
        }

        # Call Fyers history API
        response = fyers.history(data)

        # Check and calculate
        if "candles" in response and response["candles"]:
            volumes = [candle[5] for candle in response["candles"]]  # volume is at index 5
            return round(statistics.mean(volumes))
        else:
            print(f"❌ No data found for {symbol}")
            return -1

    except Exception as e:
        print(f"❌ Error fetching volume for {symbol}: {str(e)}")
        return -1

get_filtered_stocks(fyers, stocks[0:5])
"""