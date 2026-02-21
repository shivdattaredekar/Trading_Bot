# src/tradingbot/trading/order_executor.py

import os
import json
import time
from datetime import datetime
from typing import Optional
import uuid
from tradingbot.utils.logger import log
from tradingbot.trading.trade_logger import log_trade_result
from tradingbot.utils.helpers import (
    can_trade,
    order_quantity_calculator,
    validate_trade_time,
    calculate_sl_target,
)
from src.tradingbot.trading.trailing_sl import TradeTracker, load_state, save_state

# env flags
TRAILING_SIMULATE = "true"



# ----------------------------------------------------
#                   TICK HELPERS
# ----------------------------------------------------
def tick_round(price: float, tick: float) -> float:
    log(f"🔍 tick_round() → price={price}, tick={tick}")
    try:
        if tick <= 0:
            ans = round(price, 2)
            log(f"⚠️ tick <= 0, fallback round={ans}")
            return ans
        q = round(round(price / tick) * tick, 8)
        ans = float(round(q, 8))
        log(f"🔢 tick_round result = {ans}")
        return ans
    except Exception as e:
        log(f"❌ tick_round error: {e}")
        return round(price, 2)


def get_symbol_tick_size(fyers_client, symbol: str, fallback: float = 0.05) -> float:
    log(f"🔍 Fetching tick size for symbol={symbol}")
    try:
        resp = fyers_client.quotes({"symbols": symbol})
        log(f"📥 quotes() response={resp}")
        d = resp.get("d") or resp.get("data") or resp.get("quotes") or []
        if isinstance(d, list) and len(d) > 0:
            for k in ("tickSize", "tick_size", "tick"):
                if k in d[0]:
                    tick = float(d[0][k])
                    log(f"✔ Tick size for {symbol} = {tick}")
                    return tick
    except Exception as e:
        log(f"⚠️ Failed to fetch tick for {symbol}: {e}")

    log(f"⚠️ Using fallback tick={fallback} for symbol={symbol}")
    return fallback


# ----------------------------------------------------
#                     TRADE EXECUTOR
# ----------------------------------------------------
class TradeExecutor:
    def __init__(self, fyers_client=None, capital_per_trade=100, max_trades=6, trade_manager=None, trade_log_file="trades.txt"):
        log("🛠 TradeExecutor initialized")
        self.fyers = fyers_client
        self.capital = capital_per_trade
        self.max_trades = int(max_trades)
        self.trade_manager = trade_manager
        self.trade_log_file = trade_log_file
        self.trade_key = f"NIFTY_TRADE_{uuid.uuid4().hex}"


    # ------------------------------------------------
    #           QUANTITY RESOLUTION (NEW)
    # ------------------------------------------------
    def _get_lot_size(self, symbol: str) -> int:
        """
        Minimal deterministic lot-size resolver.
        Extend later if needed.
        """
        if "NIFTY" in symbol:
            return 65
        if "BANKNIFTY" in symbol:
            return 15
        if "FINNIFTY" in symbol:
            return 40
        log(f"⚠ Unknown FnO symbol for lot size: {symbol}, defaulting to 1")
        return 1

    def _resolve_quantity(self, symbol: str, price: float, risk: float, fno_lots: Optional[int]):
        """
        If fno_lots is provided → FIXED LOT FnO trade
        Else → existing risk-based calculation
        """
        if fno_lots is not None:
            lot_size = self._get_lot_size(symbol)
            qty = fno_lots * lot_size
            log(f"📦 FnO FIXED LOT quantity={qty} ({fno_lots} lots)")
            return qty

        # Existing behaviour (UNCHANGED)
        qty = order_quantity_calculator(
            self.capital,
            STOCK_PRICE=price,
            STOP_LOSS=risk
        )
        log(f"📦 Risk-based quantity={qty}")
        return qty



    # ------------------------------------------------
    #                ORDER PAYLOAD BUILDERS
    # ------------------------------------------------
    def prepare_entry_order(self, symbol: str, qty: int, side: int) -> dict:
        log(f"📦 prepare_entry_order() → symbol={symbol}, qty={qty}, side={side}")
        payload = {
            "symbol": symbol,
            "qty": qty,
            "type": 2,                 # MARKET
            "side": side,
            "productType": "INTRADAY",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "stopLoss": 0,
            "takeProfit": 0,
            "offlineOrder": False,
            "disclosedQty": 0,
        }
        log(f"📦 Entry order payload: {payload}")
        return payload

    def prepare_target_order(self, symbol:str, qty:int, target:int, entry_side:int, tick_size: float) -> dict:
        log(f"📦 prepare_TG_order() → symbol={symbol}, qty={qty}, limit price ={target}, tick={tick_size}")
        side = 1 if entry_side == -1 else -1
        payload = { 
            "symbol": symbol,
            "qty": qty/2,
            "type": 1,
            "side": side,
            "productType": "INTRADAY",
            "limitPrice": target,
            "stopPrice": 0,
            "validity": "DAY",
            "stopLoss": 0,
            "takeProfit": 0,
            "offlineOrder": False,
            "disclosedQty": 0,
            "isSliceOrder" : False 
            }
        log(f"📦 TG order payload: {payload}")
        return payload


    def prepare_sl_order(self, symbol: str, qty: int, stop_price: float, entry_side: int, tick_size: float) -> dict: 
        log(f"📦 prepare_sl_order() → symbol={symbol}, qty={qty}, raw stop={stop_price}, tick={tick_size}")
        sl_side = -1 if entry_side == 1 else 1
        sp = tick_round(stop_price, tick_size)
        sp_final = sp - 1 
        lp = sp_final - 1
        payload = {
            "symbol": symbol,
            "qty": qty,
            "type": 4,                   # SL-L
            "side": sl_side,
            "productType": "INTRADAY",
            "limitPrice": float(lp),
            "stopPrice": float(sp_final),
            "validity": "DAY",
            "offlineOrder": False,
            "disclosedQty": 0,
        }
        log(f"📦 SL order payload: {payload}")
        return payload

    # ------------------------------------------------
    #                BROKER API WRAPPERS
    # ------------------------------------------------
    def execute_order(self, order_data: dict) -> dict:
        log(f"🚀 execute_order() → payload={order_data}")
        try:
            resp = self.fyers.place_order(order_data)
            log(f"📥 Order Response: {resp}")
            return resp or {}
        except Exception as e:
            log(f"❌ place_order EXCEPTION: {e}")
            return {"code": 0, "message": str(e)}

    def _fetch_tradebook(self) -> list:
        log("📖 Fetching tradebook...")
        try:
            resp = self.fyers.tradebook()
            log(f"📖 tradebook response={resp}")
            tb = resp.get("tradeBook") or resp.get("data") or []
            log(f"📖 tradebook entries={len(tb)}")
            return tb
        except Exception as e:
            log(f"⚠️ tradebook EXCEPTION: {e}")
            return []

    # ------------------------------------------------
    #     WAIT UNTIL THE TRADEBOOK SHOWS THIS TRADE
    # ------------------------------------------------
    def _wait_for_trade_fill(self, entry_id, max_wait=12):
        log(f"⏳ _wait_for_trade_fill() → waiting for entry_id={entry_id}")
        for sec in range(max_wait):
            trades = self._fetch_tradebook()
            for tr in trades:
                if str(tr.get("orderNumber")) == str(entry_id):
                    log(f"✔ Found entry in tradebook at {sec}s")
                    return trades
            log(f"⏳ Still waiting... {sec+1}/{max_wait}")
            time.sleep(1)

        log("⚠ Trade fill not detected within wait window.")
        return self._fetch_tradebook()

    # ------------------------------------------------
    #      REGISTER ENTRY + SL IDs WITH TRAILING ENGINE
    # ------------------------------------------------
    def _register_trade(self, entry_resp: dict, sl_id: str, tg_id: str, stop_price: float):
        log("🛠 Registering trade with trailing engine...")

        entry_id = entry_resp.get("id") or entry_resp.get("orderNumber")
        log(f"➡ entry_id = {entry_id}, sl_id={sl_id}, tg_id={tg_id}, stop_price={stop_price}")

        # 1) Wait for trade fill
        trades = self._wait_for_trade_fill(entry_id)

        # 2) Load existing json state
        order_tracker, active_trades = load_state()
        tracker = TradeTracker(self.fyers, order_tracker, active_trades)

        # 3) Inject symbol + qty + side into entry_resp (important for correct trailing behavior)
        for tr in trades:
            if str(tr.get("orderNumber")) == str(entry_id):
                entry_resp["symbol"] = tr.get("symbol")
                entry_resp["qty"] = tr.get("tradedQty", tr.get("qty", 0))
                entry_resp["side"] = tr.get("side")
                break

        # 4) Add entry + SL ID
        tracker.update_trade_artifacts({"id": entry_id})
        if sl_id:
            tracker.update_trade_artifacts({"id": sl_id})
        
        if tg_id:
            tracker.update_trade_artifacts({"id": tg_id})

        # 5) Metadata for initialization
        order_data_for_tracker = {
            "stopPrice": stop_price,
            "sl_order_id": sl_id,
            "tg_order_id": tg_id
        }

        # 6) Initialize trade
        updated = tracker.update_after_trade(trades, entry_resp, order_data_for_tracker)

        # 7) Save updated persistent state
        save_state(tracker.order_tracker, updated)

        log("🔥 Trade successfully registered for trailing SL.")
        return tracker

    # ------------------------------------------------
    #               MAIN PLACE TRADE FUNCTION
    # ------------------------------------------------
    def place_trade(self, symbol: str, price: float, sl: float, target: float, timestamp: str,
                side: int = 1, mode: str = "EMA", fno_lots: Optional[int] = None):


        log("\n==============================")
        log(f"🚀 place_trade() START for {symbol}")
        log("==============================")

        try:
            # Step 1: Validate timestamp
            log(f"🕒 Checking validate_trade_time → timestamp={timestamp}")
            try:
                if not validate_trade_time(timestamp):
                    log(f"⛔ Skipping {symbol}: signal stale.")
                    return
            except Exception as e:
                log(f"⚠️ validate_trade_time exception: {e}")

            # Step 2: Compute normalized stop + target levels
            log(f"📐 calculate_sl_target(price={price}, sl={sl}, target={target})")
            SP, target = calculate_sl_target(price, sl, target)
            risk = abs(price - SP)

            log(f"📌 Computed SL={SP}, distance={risk}, normalized target={target}")

            # Step 3: Quantity (FnO-aware, backward compatible)
            qty = self._resolve_quantity(symbol, price, risk, fno_lots)

            if qty <= 0:
                log("⛔ Quantity resolved to 0. Skipping trade.")
                return
            log(f"📦 Computed quantity={qty}")

            # Step 4: Trading policy checks
            if mode.upper() != "TAMO":
                log("⚙ EMA mode trade rules apply.")

                if not can_trade(self.trade_key, self.trade_log_file):
                    log("⛔ can_trade() = False → Skipping.")
                    return

                if self.trade_manager and self.trade_manager.get_trades() >= self.max_trades:
                    log(f"⛔ Max trades ({self.max_trades}) reached. Skipping.")
                    return

            # Step 5: Tick size
            tick = get_symbol_tick_size(self.fyers, symbol)
            log(f"✔ Tick size={tick}")

            # Step 6: Place ENTRY order
            entry_order = self.prepare_entry_order(symbol, qty, side)
            entry_resp = self.execute_order(entry_order)

            if entry_resp.get("code") != 1101:
                log("❌ ENTRY FAILED. Aborting trade registration.")
                self.handle_order_response(symbol, entry_resp, price, risk, target)
                return

            entry_id = entry_resp.get("id")
            log(f"✔ ENTRY SUCCESS → entry_id={entry_id}")

            # Step 7: SL-M SL Order
            sl_order = self.prepare_sl_order(symbol, qty, SP, side, tick)
            sl_resp = self.execute_order(sl_order)
            sl_id = sl_resp.get("id") if sl_resp.get("code") == 1101 else None

            

            if sl_id:
                log(f"✔ SL ORDER SUCCESS → sl_id={sl_id}")
            else:
                log(f"⚠ SL ORDER FAILED → {sl_resp}")

            # Step 9: Target LIMIT order
            tg_order = self.prepare_target_order(symbol, qty, target, side,
                                                tick)
            tg_resp = self.execute_order(tg_order)
            tg_id = tg_resp.get("id") if tg_resp.get("code") == 1101 else None

            if tg_id:
                log(f"✔ TG ORDER SUCCESS → tg_id={tg_id}")
            else:
                log(f"⚠ TG ORDER FAILED → {tg_resp}")

            # Step 8: Register everything with trailing engine
            tracker = self._register_trade(entry_resp, sl_id, tg_id, SP)

            # Step 9: Final trading logs
            self.handle_order_response(symbol, entry_resp, price, risk, target)

        except Exception as e:
            log(f"❌ Unexpected error in place_trade(): {e}")

    # ------------------------------------------------
    #                TAMO WRAPPER
    # ------------------------------------------------
    def place_TAMO_trade(self, symbol: str, price: float, sl: float, target: float, timestamp: str, side: int):
        log(f"🚀 place_TAMO_trade() wrapper for {symbol}")
        return self.place_trade(symbol, price, sl, target, timestamp, side=side, mode="TAMO")

    # ------------------------------------------------
    #                FINAL ORDER RESPONSE
    # ------------------------------------------------
    def handle_order_response(self, symbol, response, price, sl, target):
        log(f"🧾 handle_order_response() → {symbol}, response={response}")

        if response.get("code") == 1101:
            log(f"✔ Trade SUCCESS for {symbol}")
            log_trade_result(self.trade_key or symbol, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), price, sl, target, "success")

            if self.trade_manager:
                try:
                    self.trade_manager.create_trades()
                    log("📌 trade_manager updated.")
                except Exception as e:
                    log(f"⚠ trade_manager exception: {e}")
        else:
            log(f"❌ Trade FAILED for {symbol}")
            log_trade_result(self.trade_key or symbol, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), price, sl, target, "failed")
