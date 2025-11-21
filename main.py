import os
import json
import time
import traceback
from datetime import datetime, time as dtime
from dotenv import load_dotenv

# --- Trading Bot Imports ---
from src.tradingbot.data.volumefilter import final_filter_with_volume
from src.tradingbot.data.datasocket import run_gapup_websocket
from src.tradingbot.utils.logger import log
from src.tradingbot.login.auth import get_fyers_instance, is_access_token_valid
from src.tradingbot.login.authentication import auto_login
from src.tradingbot.utils.helpers import clean_up, TRADE_LOG_FILE
from src.tradingbot.trading.trade_manager import TradeManager
from src.tradingbot.strategies.ema_strategy import EMAStrategy
from src.tradingbot.strategies.tamo_strategy import SingleStockStrategy
from src.tradingbot.trading.order_executor import TradeExecutor
from src.tradingbot.config import CAPITAL_PER_TRADE, MAX_TRADES, RR

# --- Constants ---
FILTERED_FILE = "filtered_stocks.json"
MARKET_START = dtime(9, 15)
MARKET_END = dtime(15, 0)

# --------------------------------------------------------
# 🕐 Market Hours Check
# --------------------------------------------------------
def is_market_open():
    now = datetime.now().time()
    today = datetime.now().strftime('%A')
    return MARKET_START <= now <= MARKET_END and today not in ("Saturday", "Sunday")

# --------------------------------------------------------
# 🚀 Main Trading Bot Entry Point
# --------------------------------------------------------
def main():
    log("🔹 Starting trading script...")

    # Step 0: Clean-up old trade logs
    clean_up()

    # Step 1: Authentication
    log("Authenticating with Fyers API...")
    try:
        if not is_access_token_valid():
            auto_login()
            load_dotenv(override=True)
        log("Authentication successful.")
        time.sleep(3)  # ensure access token is loaded properly
    except Exception as e:
        log(f"Authentication failed: {e}")
        return

    fyers = get_fyers_instance()

    # Step 2: Stock Filtering Logic
    if os.path.exists(FILTERED_FILE):
        log(f"Loading previously filtered stocks from {FILTERED_FILE}...")
        with open(FILTERED_FILE, "r") as f:
            filtered_stocks = json.load(f)
    else:
        log("Fetching new gap-up stocks using WebSocket...")
        try:
            run_gapup_websocket(duration=15)
            gap_file = "GapUp_stocks.json"
            if not os.path.exists(gap_file):
                with open(gap_file, "w") as f:
                    json.dump([], f)

            with open(gap_file, "r") as f:
                gapup_stocks = json.load(f)

            log(f"Gap-up stocks found: {len(gapup_stocks)}")

            # Apply volume filter with retries
            retry = 2
            filtered_stocks = []
            while retry > 0:
                try:
                    filtered_stocks = final_filter_with_volume(fyers, gapup_stocks)
                    if filtered_stocks:
                        break
                    log(f"No stocks passed volume filter. Retrying ({retry-1})...")
                except Exception as e:
                    log(f"Volume filter error: {e}")
                retry -= 1
                time.sleep(3)

            if not filtered_stocks:
                log("No stocks passed after retries. Exiting.")
                return

            with open(FILTERED_FILE, "w") as f:
                json.dump(filtered_stocks, f)

        except Exception as e:
            log(f"Error in stock filtering: {e}")
            return

    # Step 3: Initialize Trade Manager and Strategies
    # Initialize TradeManager
    TRADE_FILE = 'trades.txt'
    trade_manager = TradeManager(int(MAX_TRADES), trade_file=TRADE_FILE)
        
    executor = TradeExecutor(
        fyers=fyers,
        capital_per_trade=CAPITAL_PER_TRADE,
        max_trades=MAX_TRADES,
        trade_manager=trade_manager,
        trade_log_file=TRADE_LOG_FILE
    )

    already_traded = set()
    ema_strategy = EMAStrategy(fyers, executor, filtered_stocks, already_traded)
    tamo_strategy = SingleStockStrategy("NSE:TMPV-EQ", RR, fyers)

    log("Entering monitoring loop...")

    counter = 0
    while True:
        if not is_market_open():
            log("Market closed. Sleeping for 60 seconds.")
            time.sleep(60)
            counter += 1
            if counter >= 3:
                clean_up()
                log("Market closed for the day. Exiting...")
                break
            continue

        log(f"Checking trade setups at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            # Step 4: Apply EMA strategy
            ema_strategy.evaluate_and_trade()

            # Step 5: Apply TAMO strategy (once per day after 9:58)
            tamo_file = "./tamo.txt"
            os.makedirs(os.path.dirname(tamo_file), exist_ok=True)

            if not os.path.exists(tamo_file):
                with open(tamo_file, "w") as f:
                    f.write("")

            with open(tamo_file, "r") as f:
                tamo_flag = f.read().strip()

            if datetime.now().strftime("%H:%M") >= "09:58" and not tamo_flag:
                tamo_signal, side = tamo_strategy.evaluate_trade_signal()
                if tamo_signal:
                    executor.place_TAMO_trade(
                        "NSE:TMPV-EQ",
                        tamo_signal["entry_price"],
                        tamo_signal["stop_loss"],
                        tamo_signal["target"],
                        tamo_signal["timestamp"],
                        side
                    )


                    with open(tamo_file, "w") as f:
                        f.write(datetime.now().strftime("%Y-%m-%d"))
                    log(f"TAMO trade executed successfully at {tamo_signal['timestamp']}")
        except Exception:
            log(f"Error in trading logic:\n{traceback.format_exc()}")

        time.sleep(10)


# --------------------------------------------------------
# 🧩 Script Entry
# --------------------------------------------------------
if __name__ == "__main__":
    main()
