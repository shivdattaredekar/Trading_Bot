import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.tradingbot.utils.logger import log

from src.tradingbot.login.auth import get_fyers_instance

fyers = get_fyers_instance()

ORDER_TRACKER = "order_tracker.json"
ACTIVE_TRADES = "active_trades.json"
DEFAULT_TARGET_COUNT = 30


# -------------------------
# State helpers
# -------------------------
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


def save_state(order_tracker: List[str], active_trades: Dict[str, dict]):
    with open(ORDER_TRACKER, "w") as f:
        json.dump(order_tracker, f, indent=4, default=str)
    with open(ACTIVE_TRADES, "w") as f:
        json.dump(active_trades, f, indent=4, default=str)
    log("State saved successfully.")


# -------------------------
# Initialize trade record
# -------------------------
def initialize_trade_data(
    trades: List[dict],
    order_tracker: List[str],
    active_trades: Dict[str, dict],
    order_data: dict,
    target_count: int = DEFAULT_TARGET_COUNT,
) -> Dict[str, dict]:
    """
    Create/augment active_trades entries based on executed trades and order_data.
    - trades: list returned from fyers.tradebook()['tradeBook'] (or pre-saved json)
    - order_tracker: list of tracked order ids
    - order_data: the order payload used to place the order (should include stopPrice if available)
    """
    for trade in trades:
        order_id = trade.get("orderNumber") or trade.get("id") or trade.get("order_id")
        if not order_id:
            continue

        # Only initialize if this order id is in our order_tracker and not already active
        if order_id in order_tracker and order_id not in active_trades:
            entry = float(trade["tradePrice"])
            stop_price = None
            # Accept different keys that may be present in your order_data
            for k in ("stopPrice", "stop_price", "stopLoss"):
                if k in order_data:
                    stop_price = float(order_data[k])
                    break
            if stop_price is None:
                # fallback to a simple default (should not happen in real runs)
                log(f"⚠️ No stop price in order_data for {order_id}, using entry as stop (unsafe).")
                stop_price = entry

            risk = abs(entry - stop_price)
            if risk == 0:
                # avoid zero risk
                risk = max(entry * 0.001, 0.01)

            side = int(trade.get("side", 1))  # 1 == buy/long, -1 == sell/short

            # build targets as a list (index 0 = first target)
            if side == 1:
                targets = [round(entry + (i + 1) * risk, 5) for i in range(target_count)]
            else:
                targets = [round(entry - (i + 1) * risk, 5) for i in range(target_count)]

            active_trades[order_id] = {
                "symbol": trade["symbol"],
                "qty": int(trade.get("tradedQty", trade.get("qty", 0))),
                "entry_price": round(entry, 5),
                "stop_price": round(stop_price, 5),
                "side": side,
                "achieved_rr": 0,   # number of targets achieved so far
                "targets": targets,
                "status": "OPEN",
                "created_at": datetime.now().isoformat(),
            }

            log(f"Initialized trade {order_id} -> entry: {entry}, stop: {stop_price}, side: {side}, targets: {targets[:3]}...")

    return active_trades


# -------------------------
# TradeTracker class
# -------------------------
class TradeTracker:
    def __init__(self, fyers_client, order_tracker: List[str], active_trades: Dict[str, dict]):
        self.fyers = fyers_client
        self.order_tracker = order_tracker
        self.active_trades = active_trades

    def update_trade_artifacts(self, trade_response: dict):
        """
        Add the placed order id to order_tracker (de-duplicated).
        trade_response must contain 'id' and preferably 'code' to indicate success.
        """
        if not trade_response:
            log("❌ Empty trade_response in update_trade_artifacts")
            return

        resp_id = trade_response.get("id") or trade_response.get("orderNumber")
        if not resp_id:
            log("❌ No id found in trade_response")
            return

        if resp_id not in self.order_tracker:
            self.order_tracker.append(resp_id)
            log(f"✅ Added order id {resp_id} to order_tracker")
        else:
            log(f"⚠️ Order ID {resp_id} already present in order_tracker")

    def update_after_trade(self, trades: List[dict], trade_response: dict, order_data: dict):
        """
        Called after an order is placed and executed (or partially executed). Initializes active_trades if
        trade execution appears in the trades (tradebook).
        """
        self.active_trades = initialize_trade_data(trades, self.order_tracker, self.active_trades, order_data)
        save_state(self.order_tracker, self.active_trades)
        resp_id = trade_response.get("id") or trade_response.get("orderNumber")
        log(f"✅ Trade processed and saved with id: {resp_id}")
        return self.active_trades

    def _close_trade(self, order_id: str, reason: str):
        """Mark trade closed locally; you might also want to cancel/modify remote orders here."""
        trade = self.active_trades.get(order_id)
        if not trade:
            return
        trade["status"] = "CLOSED"
        trade["closed_at"] = datetime.now().isoformat()
        trade["close_reason"] = reason
        log(f"❌ Trade {order_id} closed. Reason: {reason}")

    def update_trailing_stops(self, symbol: str, ltp: float):
        """
        Single-symbol update. Call this for each live LTP tick you get for 'symbol'.
        """
        # iterate copy to allow modification of dict
        for order_id, trade in list(self.active_trades.items()):
            # skip trades of different symbols
            if trade.get("symbol") != symbol:
                continue

            if trade["status"] != "OPEN":
                continue

            side = int(trade["side"])
            stop_price = float(trade["stop_price"])
            entry = float(trade["entry_price"])
            achieved = int(trade["achieved_rr"])
            targets: List[float] = trade["targets"]

            # 1) Check stop-loss hit first
            if side == 1:
                # Long: price falling to or below stop closes trade
                if ltp <= stop_price:
                    self._close_trade(order_id, "SL_HIT")
                    continue
            else:
                # Short: price rising to or above stop closes trade
                if ltp >= stop_price:
                    self._close_trade(order_id, "SL_HIT")
                    continue

            # 2) Check next target
            # next_target index = achieved (0-based). Example: achieved=0 -> next_target = targets[0]
            if achieved < len(targets):
                next_target = float(targets[achieved])
                target_hit = False
                if side == 1:
                    # Long: target hit if LTP >= next_target
                    if ltp >= next_target:
                        target_hit = True
                else:
                    # Short: target hit if LTP <= next_target
                    if ltp <= next_target:
                        target_hit = True

                if target_hit:
                    # increment achieved count
                    trade["achieved_rr"] = achieved + 1
                    new_achieved = trade["achieved_rr"]

                    # Decide new SL:
                    # - on first achieved (new_achieved == 1) -> set SL to entry (breakeven)
                    # - on subsequent achieved -> set SL to previous target (i.e., targets[new_achieved - 2])
                    if new_achieved == 1:
                        new_sl = entry
                    else:
                        # previous target index = new_achieved - 2 (0-based)
                        prev_target_idx = new_achieved - 2
                        new_sl = float(targets[prev_target_idx])

                    # Ensure new_sl is on the correct side relative to current price:
                    # Long: SL must be <= current price (but above previous SL). We ensure monotonic increase.
                    # Short: SL must be >= current price (but below previous SL). We ensure monotonic decrease.
                    old_sl = float(trade["stop_price"])
                    new_sl = round(float(new_sl), 5)

                    # Safety: enforce that SL moves in the right direction (monotonic toward price)
                    if side == 1:
                        # ensure new_sl >= old_sl (moves up)
                        if new_sl < old_sl:
                            log(f"⚠️ Computed new SL {new_sl} < old SL {old_sl} for long. Using old SL.")
                            new_sl = old_sl
                        # also ensure new_sl is not above LTP (we generally allow SL to be below current price)
                    else:
                        # short: ensure new_sl <= old_sl (moves down)
                        if new_sl > old_sl:
                            log(f"⚠️ Computed new SL {new_sl} > old SL {old_sl} for short. Using old SL.")
                            new_sl = old_sl

                    # Apply new SL
                    trade["stop_price"] = new_sl

                    # Persist and ask broker to modify order
                    save_state(self.order_tracker, self.active_trades)
                    try:
                        self.modify_sl(order_id, new_sl)
                    except Exception as e:
                        log(f"⚠️ modify_sl exception for {order_id}: {e}")

                    log(f"🔁 Target achieved for {order_id} ({trade['symbol']}): achieved_rr={new_achieved}, new_sl={new_sl}, next_target={(targets[new_achieved] if new_achieved < len(targets) else 'N/A')}")
                    continue

            # else: no target hit, nothing to do
            # persist occasionally (could be throttled)
            # save_state(self.order_tracker, self.active_trades)

    def modify_sl(self, order_id: str, new_sl: float):
        """
        Modify stop price for an active order via Fyers API.
        The payload below is written generically. Adjust the keys according to Fyers' modify API.
        """
        log(f"⚙️ Modifying stop price for order {order_id} -> {new_sl}")

        # Example payload - adapt to your exact Fyers SDK method signature
        payload = {
            "id": order_id,
            # Fyers modify API may expect "stopPrice" or another key. Confirm your SDK.
            "stopPrice": float(new_sl),
            # other keys if necessary, e.g., "limitPrice": 0, "type": 3
        }

        # Uncomment the real call in production:
        # response = self.fyers.modify_order(payload)
        # log(f"Modify response: {response}")

        # For now (or in tests) we simulate:
        response = {"code": 1101, "message": "simulated modify ok", "data": payload}
        log(f"✅ SL modification simulated for {order_id} -> {new_sl}. Response: {response}")
        return response

