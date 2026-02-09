# src/main.py

import os
import json
import time
import traceback
from datetime import datetime, time as dtime
from dotenv import load_dotenv

# --- AUTH / API ---
from src.tradingbot.login.auth import get_fyers_instance, is_access_token_valid
from src.tradingbot.login.authentication import auto_login
from src.tradingbot.login.fyers_session import FyersSession


# --- UTILS ---
from src.tradingbot.utils.logger import log
from src.tradingbot.utils.helpers import clean_up, TRADE_LOG_FILE
from src.tradingbot.router.instrument_router import InstrumentRouter


# --- EXECUTION ---
from src.tradingbot.trading.order_executor import TradeExecutor
from src.tradingbot.trading.trade_manager import TradeManager

# --- STRATEGIES ---
from src.tradingbot.strategies.ema_strategy import EMAStrategy
from src.tradingbot.strategies.fno_ema_strategy import FnOStockHandler

# --- TRAILING SL RUNNER ---
from src.tradingbot.trading.trailing_sl_runner import start_trailing_runner, stop_trailing_runner

# --- CONFIG ---
from src.tradingbot.config import (
    CAPITAL_PER_TRADE,
    MAX_TRADES,
)

# --- PNL EXPORT (END OF DAY) ---
from src.tradingbot.tools.pnl_tracker import (
    load_active_trades,
    fetch_tradebook,
    build_tradewise_pnl,
    export_to_excel,
)


FILTERED_FILE = "filtered_stocks.json"
MARKET_START = dtime(9, 15)
MARKET_END = dtime(15, 0)
MARKET_CLOSED_SLEEP_SEC = 60
MAX_CLOSED_ITERS = 3


# --------------------------------------------------------
# Market hours
# --------------------------------------------------------
def is_market_open():
    now = datetime.now().time()
    today = datetime.now().strftime('%A')
    return MARKET_START <= now <= MARKET_END and today not in ("Saturday", "Sunday")


# --------------------------------------------------------
# MAIN BOT
# --------------------------------------------------------
def main():
    log("🚀 Starting Trading Bot...")

    # Step 0 — clean previous day files
    clean_up()

    # Step 1 — Authentication
    log("🔑 Authenticating with Fyers...")
    try:
        if not is_access_token_valid():
            auto_login()
            load_dotenv(override=True)
            
        fyers = get_fyers_instance()    
        FyersSession.set(fyers)
        log("🔓 Authentication Successful")
        time.sleep(3)
    except Exception as e:
        log(f"❌ Authentication failed: {e}")
        return

    

    # Step 2 — Stock Selection (STATIC for EMA only)
    log("📌 Using static stocks for EMA strategy (no gap-up websocket).")

    filtered_stocks = [
        "NSE:NIFTY50-INDEX",
    ]

        
    fno_handler = FnOStockHandler(
        fyers,
        filtered_stocks,
        symbol="NIFTY",
        side="PE"
    )

    
    
    log(f"⚡ EMA stocks locked: {filtered_stocks}")


    # Step 3 — Setup executor and strategies
    trade_manager = TradeManager(MAX_TRADES, "trades.txt")

    executor = TradeExecutor(
        fyers_client=fyers,
        capital_per_trade=CAPITAL_PER_TRADE,
        max_trades=MAX_TRADES,
        trade_manager=trade_manager,
        trade_log_file=TRADE_LOG_FILE
    )

    already_traded = set()

    ema_strategy = EMAStrategy(
        fyers=fyers,
        executor=executor,
        filtered_stocks=filtered_stocks,
        already_traded=already_traded,
        fno_handler=fno_handler
    )

    # Step 4 — Start Trailing SL Runner (background thread)
    start_trailing_runner(fyers, interval=1.0)  # 1 second polling for accuracy

    log("🎯 Entering main loop...")

    # Step 5 — Main Loop with closed-market stop after N iterations
    closed_iters_remaining = MAX_CLOSED_ITERS

    try:
        while True:
            if not is_market_open():
                log(f"⏳ Market closed. Sleeping {MARKET_CLOSED_SLEEP_SEC}s... ({closed_iters_remaining} iterations left before exit)")
                time.sleep(MARKET_CLOSED_SLEEP_SEC)
                closed_iters_remaining -= 1
                if closed_iters_remaining <= 0:
                    log("🛑 Market closed for long; exiting main loop.")
                    break
                # continue checking until we exhaust iterations
                continue
            else:
                # If market is open, reset counter
                closed_iters_remaining = MAX_CLOSED_ITERS

            try:
                log(f"🔎 Checking setups at {datetime.now().strftime('%H:%M:%S')}")

                # EMA strategy
                ema_strategy.evaluate_and_trade()


            except Exception:
                log(f"❌ Main loop error:\n{traceback.format_exc()}")

            time.sleep(2)

    finally:
        # always attempt clean shutdown
        try:
            log("🔻 Shutting down: stopping trailing runner and saving state.")

            stop_trailing_runner()
            clean_up()

            # -------------------------------
            # END-OF-DAY PNL EXPORT
            # -------------------------------
            log("📊 Running end-of-day PnL export...")

            active_trades = load_active_trades()
            tradebook = fetch_tradebook()

            rows = build_tradewise_pnl(tradebook, active_trades)
            export_to_excel(rows)

            log(f"✅ End-of-day PnL export complete. Trades exported: {len(rows)}")

        except Exception as e:
            log(f"⚠ Error during shutdown / PnL export:\n{traceback.format_exc()}")

    log("🔺 Bot stopped safely.")


# --------------------------------------------------------
# App entry
# --------------------------------------------------------
if __name__ == "__main__":
    main()
