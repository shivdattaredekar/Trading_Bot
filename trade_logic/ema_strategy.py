# strategies/ema_strategy.py
import time
from datetime import datetime, timedelta
from ..config.settings import EMA_PERIOD, ORDER_QUANTITY, SIMULATE, MAX_TRADES, DATE_FROM, DATE_TO

from ..utlis.logger import log
from ..utlis.trade_logger import log_trade_result, can_trade, TRADE_LOG_FILE


def get_5min_candles(fyers, symbol):
    try:
        # Fetch 5-minute candles for the given symbol
        data = fyers.history({
            "symbol": symbol,
            "resolution": "5",
            "date_format": "1",
            "range_from": DATE_FROM,
            "range_to": DATE_TO,
            "cont_flag": "1"
        })
        candle = data.get("candles", [])
    
        # Optional: Convert timestamp to readable format for inspection
        candles = [
            {   "day_time": datetime.fromtimestamp(c[0]).strftime("%Y-%m-%d %H:%M"),
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5]
            }
            for c in candle
        ]


        return candles
    except Exception as e:
        log(f"Error fetching candles for {symbol}: {e}")
        return []


def get_prices(candles):
    # Extract prices from the candle data
    
    try:
        price = {}
        for candle in candles:
            day_time = candle["day_time"]
            open_price = candle["open"]
            high = candle["high"]
            low = candle["low"]
            close = candle["close"]
            volume = candle["volume"]
            price[day_time] = close

        #log(f"Extracted prices for {len(price)} timestamps.")
        return price
    except Exception as e:
        log(f"Error extracting prices: {e}")
        return {}


# Calculate EMA
def calculate_ema_series(prices_dict, period):
    try:
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
        #log(f"Calculated EMA for {len(ema_values)} timestamps.")
        return ema_values
    
    except Exception as e:
        log(f"Error calculating EMA: {e}")
        return {}


def evaluate_trade_signal(candles, ema, symbol):
    try:
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

        #log(f"Generated {signals} trade signals for {symbol}.")
            #place_trade(symbol, signals[-1]["entry_price"], signals[-1]["stop_loss"], signals[-1]["target"])
        return signals
    
    except Exception as e:
        log(f"Error evaluating trade signals for {symbol}: {e}")
        return []


def place_trade(fyers,symbol, price, sl, target, timestamp):
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
        
        # Prepare order data
        order_data = {
            "symbol": symbol,
            "qty": int(ORDER_QUANTITY),
            "type": 2,  # Market order
            "side": -1,  # Sell
            "productType": "BO",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
            "stopLoss": abs(price - sl),
            "takeProfit": abs(price - target)
        }
        
        # Check if the symbol can be traded
        if not can_trade(symbol=symbol, file_path=TRADE_LOG_FILE):
            log(f"Cannot trade {symbol} as it has already been traded twice.")
            return
        
        # Place the order
        response = fyers.place_order(order_data)
        log_trade_result(symbol, datetime.now().strftime("%Y-%m-%d %H:%M"), price, sl, target, status="success")
        log(f"Trade placed successfully: {response}")
    
    except Exception as e:
        log(f"Error placing trade for {symbol}: {e}")
        log_trade_result(symbol, datetime.now().strftime("%Y-%m-%d %H:%M"), price, sl, target, status="failed", error_message=str(e))