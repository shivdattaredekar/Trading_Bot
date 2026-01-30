import os
import csv
import time
from typing import Tuple
from tradingbot.utils.logger import log
from datetime import datetime, timedelta
from tradingbot.signals.signal import TradeSignal
import traceback
from typing import Optional
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
        for i in range(1, len(candles)):
            current = candles[i]
            prev = candles[i - 1]
            ts = current["day_time"]
            
            if ts not in ema:
                continue
            
            prev_low = prev["low"]
            current_low = current["low"]
            current_close = current["close"]
            current_ema = ema[ts]

            if (
                prev_low > current_ema and
                current_low < prev_low and
                current_close > current_ema
            ):
                return {"time": ts}
        return {"time": "no signal"}
    except Exception as e:
        log(f"Error evaluating trade signals for {symbol}: {e}")
        return {"time": "no signal"}



def validate_trade_time(timestamp: str, window_minutes=5) -> bool:
    trade_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M')
    return abs(datetime.now() - trade_time) <= timedelta(minutes=window_minutes)

def calculate_sl_target(price: float, sl: float, target: float) -> Tuple[float, float]:
    St_L = round(sl, 2)
    target = round(target, 2)
    return St_L, target

def order_quantity_calculator(CAPITAL_PER_TRADE, STOCK_PRICE, STOP_LOSS):
    try:
        capital_per_trade = float(CAPITAL_PER_TRADE)
        ORDER_QUANTITY = int(capital_per_trade / STOP_LOSS)
        return max(ORDER_QUANTITY, 1)

    except Exception as e:
        log(f"Error in order quantity calculation: {e}")
        return 1


def get_ltp(fyers, symbol: str):
    """
    Minimal LTP fetcher.
    - No retries
    - Only checks classic 'd' field
    - Logs rate limit (429)
    """
    #log(f"📡 Fetching LTP for {symbol}")

    try:
        resp = fyers.quotes({"symbols": symbol})
        log(f"📥 quotes() response: message = {resp['message']}, code = {resp['code']}")

        # --- Handle rate limit ---
        if resp.get("code") == 429:
            log("⚠️ rate limit exceeded (429)")
            return None

        # --- Classic structure check ---
        d = resp.get("d")
        if not d or not isinstance(d, list):
            log("⚠️ no d found in response")
            return None

        v = d[0].get("v", {})
        ltp = v.get("lp")

        if ltp is None:
            log("⚠️ lp not found inside d[0].v")
            return None

        ltp_float = float(ltp)
        #log(f"✅ LTP for {symbol}: {ltp_float}")
        return ltp_float

    except Exception as e:
        log(f"❌ Exception in get_ltp: {e}")
        return None


def check_trades(trade_key, file_path=TRADE_LOG_FILE):
    if not os.path.exists(file_path):
        return []

    trades = []
    today = datetime.now().date()

    with open(file_path, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                trade_time = datetime.strptime(
                    row['timestamp'], '%Y-%m-%d %H:%M:%S'
                )
            except ValueError:
                continue

            if (
                row["symbol"] == trade_key and
                trade_time.date() == today and
                row["status"] == "success"
            ):
                trades.append(trade_time)

    return trades

def can_trade(trade_key, file_path=TRADE_LOG_FILE):
    trades = check_trades(trade_key, file_path)

    # Rule 1: Max 2 trades per day
    if len(trades) >= 2:
        log(f"⛔ Max daily trades reached for {trade_key}")
        return False

    # Rule 2: Cooldown — 10 minutes from last trade
    if trades:
        last_trade_time = max(trades)
        if (datetime.now() - last_trade_time).total_seconds() < 600:
            log(f"⏳ Cooldown active for {trade_key}")
            return False

    return True



from datetime import datetime, time
import os, shutil

def clean_up():
    filenames = [
        'filtered_stocks.csv',
        'filtered_stocks.json',
        'gapup_data.csv',
        'gapup_data.json',
        'trades.txt',
        'GapUp_stocks.json',
        'tamo.txt',
        "active_trades.json",
        "order_tracker.json",
    ]

    curr_time = datetime.now().time()
    market_start = time(9, 20)
    market_end = time(15, 00)

    try:
        if market_start <= curr_time <= market_end:
            log("🕒 Market hours detected — no cleanup or backup.")
            return

        log("🧹 Market closed — performing cleanup with backup.")

        today = datetime.now().strftime("%Y-%m-%d")
        backup_dir = os.path.join("backup", today)
        os.makedirs(backup_dir, exist_ok=True)

        for file in filenames:
            if os.path.exists(file):
                shutil.move(file, os.path.join(backup_dir, file))
                log(f"📦 Backed up & removed: {file}")
            else:
                log(f"⚠️ File not found: {file}")

    except Exception as e:
        log(f"❌ Error during cleanup: {e}")




