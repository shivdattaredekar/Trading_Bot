# src/tradingbot/trading/trailing_sl_runner.py

import threading
import time
from typing import Optional
from src.tradingbot.utils.logger import log

from src.tradingbot.trading.trailing_sl import (
    TradeTracker,
    load_state,
    save_state
)

from src.tradingbot.utils.helpers import get_ltp


class TrailingSLRunner:
    """
    Background thread that reloads state every cycle, fetches LTP,
    and updates trailing stops for all active trades.
    """

    def __init__(self, fyers, interval: float = 1.0):
        log("📥 [Runner.__init__] Initializing TrailingSLRunner...")

        self.fyers = fyers
        self.interval = max(0.2, float(interval))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._lock = threading.Lock()

        # Load initial state
        order_tracker, active_trades = load_state()
        log(f"📚 [Runner.__init__] Loaded: {len(order_tracker)} order_ids, "
            f"{len(active_trades)} active trades")

        self.tracker = TradeTracker(self.fyers, order_tracker, active_trades)

    # ----------------------------------------------------------------------
    def _loop(self):
        log("🟢 [Runner] TrailingSLRunner started.")

        while not self._stop_event.is_set():
            try:
                # Reload state at each cycle
                with self._lock:
                    order_tracker, active_trades = load_state()
                    self.tracker.order_tracker = order_tracker
                    self.tracker.active_trades = active_trades

                active_count = len(active_trades)
                log(f"🔁 [Runner] Reloaded state → {active_count} active trades")

                if active_count == 0:
                    time.sleep(self.interval)
                    continue

                # Snapshot prevents mutation during iteration
                snapshot = dict(active_trades)

                for order_id, trade in snapshot.items():

                    # Skip CLOSED trades immediately
                    if trade.get("status") == "CLOSED":
                        log(f"⏭️ [Runner] order_id={order_id} is CLOSED — skipping.")
                        continue

                    if trade.get("status") == "EXITING":
                        log(f"⏳ [Runner] order_id={order_id} EXITING — waiting for engine.")
                        continue

                    try:
                        log(f"➡️ [Runner] Processing order_id={order_id}")

                        symbol = trade.get("symbol")
                        if not symbol:
                            log(f"⚠️ [Runner] order_id={order_id} missing symbol — skip")
                            continue

                        # Fetch LTP with safe wrapper
                        log(f"🔎 [Runner] Fetching LTP for {symbol}")
                        ltp = get_ltp(self.fyers, symbol)

                        if ltp is None:
                            log(f"⚠️ [Runner] LTP None for {symbol} — skip tick")
                            continue

                        #log(f"📈 [Runner] {symbol} LTP = {ltp}")

                        # Update trailing logic
                        with self._lock:
                            log(f"🔧 [Runner] update_trailing_stops({symbol}, ltp={ltp})")
                            self.tracker.update_trailing_stops(symbol, float(ltp))

                            save_state(self.tracker.order_tracker, self.tracker.active_trades)
                            log("💾 [Runner] State saved")

                    except Exception as inner_e:
                        log(f"🔥 [Runner] Error while processing {order_id}: {inner_e}")

                time.sleep(self.interval)

            except Exception as e:
                log(f"🔥 [Runner] Outer loop error: {e}")
                time.sleep(self.interval)

        # Final save on stop
        try:
            with self._lock:
                save_state(self.tracker.order_tracker, self.tracker.active_trades)
            log("💾 [Runner] Final state saved on exit")
        except Exception as e:
            log(f"🔥 [Runner] Final save exception: {e}")

        log("🔴 [Runner] TrailingSLRunner stopped.")

    # ----------------------------------------------------------------------
    def start(self):
        log("▶️ [Runner.start] Starting TrailingSLRunner...")

        if self._thread and self._thread.is_alive():
            log("⚠️ [Runner.start] Runner already running.")
            return self._thread

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="TrailingSLRunner"
        )
        self._thread.start()

        log("✅ [Runner.start] Runner thread started.")
        return self._thread

    # ----------------------------------------------------------------------
    def stop(self, timeout: float = 5.0):
        log("🛑 [Runner.stop] Stopping TrailingSLRunner...")

        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=timeout)

            if self._thread.is_alive():
                log("⚠️ [Runner.stop] Runner did not stop within timeout.")
            else:
                log("🟢 [Runner.stop] Runner stopped successfully.")


# ----------------------------------------------------------------------
# Global convenience wrapper
# ----------------------------------------------------------------------

_runner_instance: Optional[TrailingSLRunner] = None


def start_trailing_runner(fyers, interval: float = 1.0) -> TrailingSLRunner:
    global _runner_instance
    log("▶️ [start_trailing_runner] Start request received.")

    if _runner_instance is None:
        log("➡️ [start_trailing_runner] Creating new TrailingSLRunner instance.")
        _runner_instance = TrailingSLRunner(fyers, interval)
        _runner_instance.start()
    else:
        log("⚠️ [start_trailing_runner] Already running — using existing.")

    return _runner_instance


def stop_trailing_runner():
    global _runner_instance
    log("🛑 [stop_trailing_runner] Stop request received.")

    if _runner_instance:
        _runner_instance.stop()
        _runner_instance = None
        log("🟢 [stop_trailing_runner] Runner stopped & cleared.")
    else:
        log("⚠️ [stop_trailing_runner] No runner running.")
