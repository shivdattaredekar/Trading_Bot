import os
import csv
import time
from typing import Tuple
from tradingbot.utils.logger import log
from datetime import datetime, timedelta
import traceback
from tradingbot.config import (
    EMA_PERIOD,
    CAPITAL_PER_TRADE,
    SIMULATE,
    MAX_TRADES,
    RR,
    CAPITAL
)
import json


# ------------------
# 5 EMA helpers 
# ------------------

TRADE_LOG_FILE = "trade_log.csv"
ORDER_TRACKER = "order_tracker.json"
ACTIVE_TRADES = "active_trades.json"

# Load NSE holidays
import requests
from datetime import datetime, timedelta

def load_nse_holidays(year=None):
    """
    Fetch NSE trading holidays (equity market) for a given year.
    Returns a set of date objects.
    """

    url = "https://www.nseindia.com/api/holiday-master?type=trading"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }

    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)  # Load cookies
    response = session.get(url, headers=headers)

    data = response.json()

    holidays = set()

    for item in data.get("CM", []):    # CM = Capital Market (equity)
        date_str = item["tradingDate"]  # Format: '26-Feb-2025'
        dt = datetime.strptime(date_str, "%d-%b-%Y").date()

        if year is None or dt.year == year:
            holidays.add(dt)

    return holidays

# Get last trading holiday
HOLIDAYS = load_nse_holidays(datetime.now().year)

def is_holiday(date):
    return date in HOLIDAYS or date.weekday() >= 5


def get_last_trading_day(today=None):
    if today is None:
        today = datetime.now().date()

    d = today - timedelta(days=1)

    while is_holiday(d):  
        d -= timedelta(days=1)
    return d

DATE_FROM = get_last_trading_day()
DATE_TO   = datetime.now().date()


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
        
        if len(prices) < period:  # 👈 Prevent IndexError
            log(f"Not enough data to calculate EMA. Needed {period}, got {len(prices)}.")
            return {}
        
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
        return signals
    
    except Exception as e:
        log(f"Error evaluating trade signals for {symbol}: {e}")
        return []


def validate_trade_time(timestamp: str, window_minutes=5) -> bool:
    trade_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M')
    return abs(datetime.now() - trade_time) <= timedelta(minutes=window_minutes)

def calculate_sl_target(price: float, sl: float, target: float) -> Tuple[float, float]:
    St_L = abs(price - sl)

    if St_L >= abs(0.01 * price):
        St_L = abs(0.01 * price)
        target = abs(price - 3 * St_L)
    elif St_L <= 0.5:
        St_L = 0.51
        target = abs(price - 3 * St_L)
    
    return round(St_L, 2), round(target, 2)

def check_trades(symbol, file_path=TRADE_LOG_FILE):
    if not os.path.exists(file_path):
        return []

    # Read trades for the given symbol from the CSV file
    trades = []
    with open(file_path, mode="r") as file:
        reader = csv.DictReader(file)
        today = datetime.now().strftime("%Y-%m-%d")
        for row in reader:
            # Check for trade date 
            trade_date = datetime.strptime(row['timestamp'],'%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d")

            # Check for the symbol and if it is traded today and the status is successful
            if row["symbol"] == symbol and trade_date == today and row['status'] == 'success':
                trades.append(row)
    return trades

def order_quantity_calculator(CAPITAL_PER_TRADE, STOCK_PRICE, STOP_LOSS):
    try:
        capital_per_trade = float(CAPITAL_PER_TRADE)
        ORDER_QUANTITY = int(capital_per_trade / max(STOP_LOSS, 0.51))
        return max(ORDER_QUANTITY, 1)

    except Exception as e:
        log(f"Error in order quantity calculation: {e}")
        return 1




# If trades for any symbol are equal to two then don't trade again on that symbol 

def can_trade(symbol, file_path=TRADE_LOG_FILE):
    trades = check_trades(symbol, file_path)

    # Rule 1: Block if already 2 or more trades
    if len(trades) >= 2:
        return False

    # Rule 2: Find the most recent trade for this symbol
    latest_trade_time = None
    with open(file_path, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["symbol"] == symbol and row["status"] == "success":
                # Parse timestamp with flexible format
                try:
                    timestamp = datetime.strptime(row['timestamp'], '%d-%m-%Y %H:%M')
                except ValueError:
                    timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')

                if latest_trade_time is None or timestamp > latest_trade_time:
                    latest_trade_time = timestamp

    # Rule 3: If a trade exists and it's within 10 minutes, block
    if latest_trade_time and (datetime.now() - latest_trade_time).total_seconds() < 600:
        log(f"Cannot trade {symbol} as it has already been traded within 10 minutes.")
        return False

    # Otherwise, allow trade
    return True



def clean_up():
    filenames = [
        'filtered_stocks.csv',
        'filtered_stocks.json',
        'gapup_data.csv',
        'gapup_data.json',
        'trades.txt',
        'GapUp_stocks.json',
        'tamo.txt'
    ]
    
    for file in filenames:
        try:
            if os.path.exists(file):
                # if file is empty → delete it (start of day scenario)
                os.remove(file)
                log(f"file {file} deleted successfully")
                    
            else:
                log(f"file {file} does not exist")
        
        except Exception as e:
            log(f"Error deleting file {file}: {e}")



def load_state():
    if os.path.exists(ORDER_TRACKER):
        with open(ORDER_TRACKER, "r") as f:
            order_tracker = json.load(f)
    else:
        order_tracker = []
    
    if os.path.exists(ACTIVE_TRADES):
        with open(ACTIVE_TRADES, "r") as f:
            active_trades = json.load(f)
    else:
        active_trades = {}
    return order_tracker, active_trades

def save_state(order_tracker, active_trades):
    with open(ORDER_TRACKER, "w") as f:
        json.dump(order_tracker, f, indent=4)
    with open(ACTIVE_TRADES, "w") as f:
        json.dump(active_trades, f, indent=4)
        log("State saved successfully.")


def get_LTP(symbol, fyers):
    candle = get_5min_candles(fyers, symbol)
    price_dict = get_prices(candle)
    LTP_time = list(price_dict.keys())[-1]
    LTP = price_dict[LTP_time]
    return LTP
