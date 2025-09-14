# strategies/ema_strategy.py
import time
from datetime import datetime, timedelta
import traceback
from tradingsetup.config.settings import (
    EMA_PERIOD,
    CAPITAL_PER_TRADE,
    SIMULATE,
    MAX_TRADES,
    DATE_FROM,
    DATE_TO,
    RR,
    CAPITAL
)
from tradingsetup.utlis.logger import log
from tradingsetup.utlis.trade_logger import (
    log_trade_result,
    can_trade,
    TRADE_LOG_FILE,
    order_quantity_calculator,
    TradeManager
)

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
    
    except Exception :
        log(f"Error calculating EMA: \n{traceback.format_exc()}")
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
                    "target": prev_low - int(RR) * (prev["high"] - prev_low)
                })

        #log(f"Generated {signals} trade signals for {symbol}.")
            #place_trade(symbol, signals[-1]["entry_price"], signals[-1]["stop_loss"], signals[-1]["target"])
        return signals
    
    except Exception as e:
        log(f"Error evaluating trade signals for {symbol}: {e}")
        return []

# Initialize TradeManager
trade_manager = TradeManager(int(MAX_TRADES))

def place_trade(fyers, symbol, price, sl, target, timestamp):
    
    """
    Places a trade using the Fyers API.
    Args:
        fyers: Fyers API client instance.
        symbol (str): Stock symbol to trade.
        price (float): Entry price for the trade.
        sl (float): Stop loss price.
        target (float): Target price.
        timestamp (str): Timestamp of the trade signal.
        max_trades (int): Maximum trades allowed per day.
    Returns:
        None
    """
    global trade_manager

    try:

        # Check if the current time is within the trading window
        trade_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M')
        trade_delta = abs(datetime.now() - trade_time)
        
        if trade_delta > timedelta(minutes=5):
            log(f"Trade for {symbol} at {timestamp} is outside the trading window. as current time is {datetime.now().time()} hence Skipping.")
            return

        # Place the trade using Fyers API
        #log(f"Placing trade for {symbol} at price {price:.2f} with SL {sl:2f} and Target {target:.2f}.")

        # Calculate order quantity based on CAPITAL_PER_TRADE and current price
        ORDER_QUANTITY = order_quantity_calculator(CAPITAL_PER_TRADE, STOCK_PRICE=price, STOP_LOSS=sl)
        log(f"Calculated order quantity for {symbol}: {ORDER_QUANTITY} shares based on CAPITAL_PER_TRADE: {CAPITAL_PER_TRADE} and stock price: {price}")

        # Calculating SL
        St_L = abs(price - sl)

        if St_L >= abs(0.01* price):
            St_L = abs(0.01* price)
            target = abs(price - 3*St_L)

        elif St_L <= 0.5:
            St_L = 0.51
            target = abs(price - 3*St_L)
        else:
            St_L = St_L
            target = target
        log(f"Final SL: {St_L:.2f}, Final Target: {target:.2f}")

        # Prepare order data
        order_data = {
            "symbol": symbol,
            "qty": ORDER_QUANTITY,
            "type": 2,  # Market order
            "side": -1,  # Sell
            "productType": "BO",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
            "stopLoss": St_L,
            "takeProfit": abs(price - target)
        }
                

        if can_trade(symbol=symbol, file_path=TRADE_LOG_FILE):        
            # Update trade counts
            if trade_manager.get_trades() >= int(MAX_TRADES):
                log(f"Maximum trades reached for today. Cannot place more trades.")
                return
            else:    
                # Place the order
                response = fyers.place_order(order_data)
                log_trade_result(symbol, datetime.now().strftime("%Y-%m-%d %H:%M"), price, sl, target, status="success")
                log(f"Trade placed successfully: {response}")
                trade_manager.create_trades()
        else:
            log(f"Cannot trade {symbol} as it has already been traded twice today.")
    
            
    except Exception as e:
        log(f"Error placing trade for {symbol}: {e}")
        log_trade_result(symbol, datetime.now().strftime("%Y-%m-%d %H:%M"), price, sl, target, status="failed", error_message=str(e))