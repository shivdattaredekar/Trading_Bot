# src/tradingbot/trading/trailing_sl.py

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Optional

from src.tradingbot.utils.logger import log
from src.tradingbot.login.fyers_session import FyersSession


ORDER_TRACKER = "order_tracker.json"
ACTIVE_TRADES = "active_trades.json"

# Trailing parameters (user configurable)
TRAILING_RR = 3
TARGET_COUNT = int(os.getenv("TARGET_COUNT", 30))
TICK_FALLBACK = 0.05

# -------------------------
# STATE LOAD & SAVE
# -------------------------
def load_state():
    log("📥 Loading order_tracker & active_trades from JSON...")
    if os.path.exists(ORDER_TRACKER):
        with open(ORDER_TRACKER, "r") as f:
            order_tracker = json.load(f)
    else:
        log("⚠️ ORDER_TRACKER not found. Using empty list.")
        order_tracker = []

    if os.path.exists(ACTIVE_TRADES):
        with open(ACTIVE_TRADES, "r") as f:
            active_trades = json.load(f)
    else:
        log("⚠️ ACTIVE_TRADES not found. Using empty dict.")
        active_trades = {}

    log(f"📌 Loaded order_tracker={order_tracker}")
    log(f"📌 Loaded active_trades count={len(active_trades)}")
    return order_tracker, active_trades

def save_state(order_tracker, active_trades):
    if order_tracker == [] and active_trades == {}:
        log("⚠️ Skip saving: empty state detected (safety).")
        return

    log("💾 Saving state → order_tracker.json + active_trades.json")

    tmp1 = ORDER_TRACKER + ".tmp"
    tmp2 = ACTIVE_TRADES + ".tmp"

    with open(tmp1, "w") as f:
        json.dump(order_tracker, f, indent=4)
    with open(tmp2, "w") as f:
        json.dump(active_trades, f, indent=4)

    os.replace(tmp1, ORDER_TRACKER)
    os.replace(tmp2, ACTIVE_TRADES)

    log("💾 State saved successfully.")

# -------------------------
# TICK HELPERS
# -------------------------
def tick_round(price: float, tick: float) -> float:
    try:
        if tick <= 0:
            return round(price, 2)
        q = round(round(price / tick) * tick, 8)
        return float(round(q, 8))
    except Exception as e:
        log(f"⚠️ tick_round error: {e}")
        return round(price, 2)

def get_symbol_tick_size(symbol: str) -> float:
    log(f"🔍 Fetching tick size for {symbol}...")
    try:
        fyers = FyersSession.get()
        resp = fyers.quotes({"symbols": symbol})
        d = resp.get("d") or resp.get("data") or []
        if isinstance(d, list) and len(d) > 0:
            for key in ["tickSize", "tick_size", "tick"]:
                if key in d[0]:
                    tick = float(d[0][key])
                    log(f"🔎 Tick size for {symbol} = {tick}")
                    return tick
    except Exception as e:
        log(f"⚠️ Tick size lookup failed for {symbol}: {e}")

    log(f"⚠️ Tick size fallback used = {TICK_FALLBACK}")
    return TICK_FALLBACK

# -------------------------
# TRADE INIT / TRACKER
# -------------------------
def initialize_trade_data(trades, order_tracker, active_trades, order_data):
    log("🚀 Running initialize_trade_data()...")
    for tr in trades:
        order_id = tr.get("orderNumber")
        log(f"➡️ Inspecting trade from tradebook: order_id={order_id}")

        if not order_id:
            continue
        if order_id not in order_tracker:
            continue
        if order_id in active_trades:
            log(f"⏭️ order_id {order_id} already initialized. Skipping...")
            continue

        entry = float(tr.get("tradePrice") or tr.get("price") or tr.get("avgPrice") or 0)
        stop_price = float(order_data.get("stopPrice", entry))
        risk = abs(entry - stop_price)
        if risk <= 0:
            risk = max(entry * 0.001, 0.05)
        side = int(tr.get("side", 1))

        if side == 1:
            targets = [round(entry + (i + 1) * risk, 5) for i in range(TARGET_COUNT)]
        else:
            targets = [round(entry - (i + 1) * risk, 5) for i in range(TARGET_COUNT)]

        active_trades[order_id] = {
            "symbol": tr.get("symbol"),
            "qty": int(tr.get("tradedQty", tr.get("qty", 0))),
            "entry_price": entry,
            "stop_price": stop_price,
            "side": side,
            "achieved_rr": 0,
            "targets": targets,
            "status": "OPEN",           # OPEN -> EXITING -> CLOSED
            "created_at": datetime.now().isoformat(),
            "sl_order_id": order_data.get("sl_order_id"),
            "tg_order_id": order_data.get("tg_order_id"),
        }

        log(f"✅ Initialized trade {order_id}: side={side}, entry={entry}, SL={stop_price}")
    return active_trades

class TradeTracker:
    def __init__(self, fyers_client, order_tracker, active_trades):
        log("🔧 TradeTracker initialized.")
        self.fyers = fyers_client
        self.order_tracker = order_tracker or []
        self.active_trades = active_trades or {}

    def update_trade_artifacts(self, trade_response):
        oid = trade_response.get("id")
        if not oid:
            return
        if oid not in self.order_tracker:
            self.order_tracker.append(oid)
            log(f"🆕 Added order id → {oid}")

    def update_after_trade(self, trades, trade_response, order_data):
        self.active_trades = initialize_trade_data(trades, self.order_tracker, self.active_trades, order_data)
        save_state(self.order_tracker, self.active_trades)
        return self.active_trades

    def modify_sl(self, sl_order_id: str, new_sl: float, symbol: str, qty:int):
        tick = get_symbol_tick_size(symbol)
        new_sl = tick_round(new_sl, tick)

        payload = {
            "id": sl_order_id,
            "type": 4,                 # SL-L modify
            "stopPrice": float(new_sl),
            "limitPrice": float(new_sl + 1),
            "qty": qty
        }

        try:
            resp = self.fyers.modify_order(payload)
            log(f"🔧 SL Modify Response → {resp}")
            return resp
        except Exception as e:
            log(f"❌ Modify SL EXCEPTION: {e}")
            return {"error": str(e)}



    # -------------------------
    # Broker helpers (defensive)
    # -------------------------
    def _fetch_orderbook(self):
        """
        Try to fetch orderbook / orders entries to inspect order status.
        Robust to multiple response shapes.
        """
        try:
            resp = self.fyers.orderbook() if hasattr(self.fyers, "orderbook") else self.fyers.orders()
            log(f"📥 orderbook response={resp}")
            # try common keys
            orders = resp.get("orders") or resp.get("data") or resp.get("d") or resp.get("orderBook") or []
            # if orders wrapped under tradeBook etc.
            if isinstance(orders, dict):
                # flatten to list of dicts
                orders_list = []
                for v in orders.values():
                    if isinstance(v, list):
                        orders_list.extend(v)
                if orders_list:
                    return orders_list
            return orders if isinstance(orders, list) else []
        except Exception as e:
            log(f"⚠️ _fetch_orderbook exception: {e}")
            return []

    def _get_order_status(self, order_id: str) -> Dict:
        """
        Return a normalized dict describing order status for given order_id.
        If not found, returns {}.
        """
        try:
            orders = self._fetch_orderbook()
            for o in orders:
                # common keys
                oid = o.get("orderNumber") or o.get("id") or o.get("order_id") or o.get("orderNumber")
                if str(oid) == str(order_id):
                    return o
            return {}
        except Exception as e:
            log(f"⚠️ _get_order_status exception: {e}")
            return {}

    def _fetch_tradebook(self):
        """
        Fetch tradebook to compute traded quantities if needed.
        """
        try:
            resp = self.fyers.tradebook()
            log(f"📥 tradebook response={resp}")
            tb = resp.get("tradeBook") or resp.get("data") or resp.get("d") or []
            # normalize to list
            if isinstance(tb, dict):
                # flatten
                flat = []
                for v in tb.values():
                    if isinstance(v, list):
                        flat.extend(v)
                return flat
            return tb if isinstance(tb, list) else []
        except Exception as e:
            log(f"⚠️ _fetch_tradebook exception: {e}")
            return []

    def _cancel_order_safe(self, order_id: str):
        try:
            log(f"🛑 Canceling order {order_id}")
            resp = self.fyers.cancel_order({"id": order_id})
            log(f"🧽 cancel_order response: {resp['code']}")
            return resp
        except Exception as e:
            log(f"❌ cancel_order EXCEPTION for {order_id}: {e}")
            return None

    def _place_market_exit(self, symbol: str, qty: int, exit_side: int) -> Dict:
        """
        Place a market order (type=2 per FYERS V3).
        """
        payload = {
            "symbol": symbol,
            "qty": qty,
            "type": 2,               # MARKET
            "side": exit_side,
            "productType": "INTRADAY",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "offlineOrder": False,
            "disclosedQty": 0,
        }
        try:
            log(f"🚨 FORCE MARKET EXIT → payload={payload}")
            resp = self.fyers.place_order(payload)
            log(f"📥 MARKET EXIT RESPONSE: {resp}")
            return resp or {}
        except Exception as e:
            log(f"❌ MARKET EXIT EXCEPTION: {e}")
            return {"error": str(e)}

    # -------------------------
    # Main trailing logic with race-free exit
    # -------------------------
    def update_trailing_stops(self, symbol: str, ltp: float):
        #log(f"\n📡 update_trailing_stops() → symbol={symbol}, ltp={ltp}")

        for oid, trade in list(self.active_trades.items()):
            log(f"\n➡️ Checking trade oid={oid}")

            if trade.get("status") != "OPEN":
                log(f"⏭️ Trade {oid} status={trade.get('status')} - skipping")
                continue

            if trade.get("symbol") != symbol:
                log(f"⏭️ Symbol mismatch → trade_symbol={trade.get('symbol')} != {symbol}")
                continue

            side = int(trade["side"])                 # -1 short, +1 long
            stop = float(trade["stop_price"])
            entry = float(trade["entry_price"])
            qty = int(trade.get("qty", 0))

            sl_order_id = trade.get("sl_order_id")
            tg_order_id = trade.get("tg_order_id")


            risk = abs(entry - stop)
            if risk <= 0:
                log("⚠️ Invalid risk — skipping trailing")
                continue

            # -------------------------------------------------
            # 1️⃣ SL HIT CHECK (UNCHANGED — DO NOT TOUCH)
            # -------------------------------------------------
            sl_hit = False
            if side == -1 and ltp >= stop:
                sl_hit = True
            if side == 1 and ltp <= stop:
                sl_hit = True

            if sl_hit:
                log(f"⚠️ SL HIT DETECTED → oid={oid}, stop={stop}, ltp={ltp}")

                trade["status"] = "EXITING"
                save_state(self.order_tracker, self.active_trades)

                if sl_order_id:
                    log("Bhaai SL hit hua hai")

                traded_qty = 0
                try:
                    tb = self._fetch_tradebook()
                    for t in tb:
                        if str(t.get("orderNumber") or t.get("order_id")) == str(oid):
                            traded_qty += int(t.get("tradedQty", 0))
                except Exception as e:
                    log(f"⚠️ Tradebook qty calc failed: {e}")

                remaining_qty = max(0, qty - traded_qty)
                log(f"🔎 traded_qty={traded_qty}, remaining_qty={remaining_qty}")

                if remaining_qty <= 0:
                    trade["status"] = "CLOSED"
                    trade["closed_at"] = datetime.now().isoformat()
                    save_state(self.order_tracker, self.active_trades)
                    continue

                exit_side = 1 if side == -1 else -1
                exit_resp = self._place_market_exit(symbol, remaining_qty, exit_side)

                trade["status"] = "CLOSED"
                trade["closed_at"] = datetime.now().isoformat()
                trade["exit_resp"] = exit_resp

                exit_id = exit_resp.get("id") or exit_resp.get("orderNumber")
                if exit_id and exit_id not in self.order_tracker:
                    self.order_tracker.append(exit_id)

                save_state(self.order_tracker, self.active_trades)
                continue

            # -------------------------------------------------
            # 2️⃣ LAGGING RR TRAILING LOGIC (NEW)
            # -------------------------------------------------
            current_rr = abs(ltp - entry) / risk

            if current_rr < TRAILING_RR:
                log(f"⏸️ RR={current_rr:.2f} < TRAILING_START_RR — no trailing")
                continue

            trail_rr = current_rr - 1.5
            if trail_rr <= 0:
                continue

            # Compute new SL from RR
            if side == -1:  # SHORT
                new_sl = entry - (trail_rr * risk)
                should_move = new_sl < stop
            else:           # LONG
                new_sl = entry + (trail_rr * risk)
                should_move = new_sl > stop

            if not should_move:
                log(f"⏭️ RR={current_rr:.2f} → SL already better ({stop})")
                continue

            tick = get_symbol_tick_size(symbol)
            new_sl = tick_round(new_sl, tick)

            # -------------------------------------------------
            # 3️⃣ APPLY TRAIL
            # -------------------------------------------------
            log(
                f"🔁 RR={current_rr:.2f} → "
                f"SL moved to {trail_rr:.2f}R (price={new_sl}) and at (qty={qty})"
            )

            #trade["stop_price"] = new_sl
            trade["achieved_rr"] = int(current_rr)

            TRAILING_RR+=1
            
            if sl_order_id:
                if qty == 65:
                    new_var = qty
                    self.modify_sl(sl_order_id, new_sl, symbol, new_var)
                self.modify_sl(sl_order_id, new_sl, symbol, 65)
                log(f"✅ Trailing SL applied to {new_sl}")
            save_state(self.order_tracker, self.active_trades)
