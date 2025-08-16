import os
import json
import time
import asyncio 
from datetime import datetime, time as dtime
import traceback

from src.tradingsetup.stock_filter.filter_logic import final_filter_with_volume
from src.tradingsetup.stock_filter.datasocket import run_gapup_websocket
from src.tradingsetup.trade_logic.trade_executor import apply_trade_logic
from src.tradingsetup.utlis.logger import log
from src.tradingsetup.login.auth import get_fyers_instance
from src.tradingsetup.login.fyers_auto_login import auto_login
from src.tradingsetup.rate_limiter.counter import RateLimiter

# Importing Datafiles
FILTERED_FILE = "filtered_stocks.json"
MARKET_START = dtime(9, 15)
MARKET_END = dtime(15, 15)

# Checking for market condition
def is_market_open():
    now = datetime.now().time()
    return MARKET_START <= now <= MARKET_END

def main():
    log("Starting trading script...")

    # Step 1: Authentication
    if os.getenv("FYERS_ACCESS_TOKEN") is None:
        log("FYERS_ACCESS_TOKEN not found. Authenticating...")
        auto_login()
        log("Authentication successful.")

    fyers = get_fyers_instance()
    log("Authenticated Fyers instance created.")

    # Step 2: Filtering logic
    if os.path.exists(FILTERED_FILE):
        log(f"Loading filtered stocks from {FILTERED_FILE}...")
        with open(FILTERED_FILE, "r") as f:
            filtered_stocks = json.load(f)
        log(f"Loaded {len(filtered_stocks)} stocks.")
        log("Stocks to be traded: " + ", ".join(filtered_stocks) if filtered_stocks else "None")
    else:
        log("Fetching index symbols and running filtering stages...")
        try:
            rate_limiter = RateLimiter()

            # Stage 1: GAP-UP based filtering
            log("Starting WebSocket to fetch gap-up stocks...")
            run_gapup_websocket(duration=10)
            
            if not os.path.exists("GapUp_stocks.json"):
                log("No GapUp_stocks.json file  stocks found.")
                # create the file
                with open("GapUp_stocks.json", "w") as f:
                    json.dump([], f)

            with open("GapUp_stocks.json", "r") as f:
                gapup_stocks = json.load(f)
            log(f"Gap-up stocks loaded: {len(gapup_stocks)}")

            # Stage 2: Volume filtering only on shortlisted
            filtered_stocks = asyncio.run(
                final_filter_with_volume(fyers, gapup_stocks, rate_limiter)
            )
            log(f"Final filtered stocks after volume check: {len(filtered_stocks)}")
            log("Stocks to be traded: " + ", ".join(filtered_stocks) if filtered_stocks else "None")

            with open(FILTERED_FILE, "w") as f:
                json.dump(filtered_stocks, f)
            log(f"Filtered stocks saved to {FILTERED_FILE}.")
        
        except Exception as e:
            log(f"Error in filtering stocks: {e}")
            return

    # Step 3: Start monitoring
    log("Entering monitoring loop...")
    already_traded = set()

    while True:
        counter = 0
        if not is_market_open():
            log("Market closed. Sleeping for 60 seconds.")
            time.sleep(60)
            counter += 1
            if counter == 3:
                log("Market closed for 5 minutes. Exiting.")
                break
            continue

        log(f"Heartbeat: Checking for trade setups at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            apply_trade_logic(fyers, filtered_stocks, already_traded)
        except Exception :
            log(f"Error in trade logic: \n {traceback.format_exc()}")

        time.sleep(10)

if __name__ == "__main__":
    main()
