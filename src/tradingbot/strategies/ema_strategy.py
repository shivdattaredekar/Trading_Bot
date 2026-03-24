from datetime import datetime
from tradingbot.utils.logger import log
from tradingbot.utils.helpers import (
    get_5min_candles,
    get_prices,
    calculate_ema_series,
    evaluate_trade_signal,
    get_ltp
)
from tradingbot.strategies.base_strategy import BaseStrategy
from tradingbot.config import EMA_PERIOD

from tradingbot.config import RR, LOTS


class OptionContext:
    def __init__(self):
        self.symbol = None
        self.ltp = None
        self.timestamp = None
        self.SL = None
        self.TG = None
        self.time = None

class EMAStrategy(BaseStrategy):
    def __init__(self, fyers, executor, filtered_stocks, already_traded, fno_handler):
        super().__init__(fyers, executor)
        self.filtered_stocks = filtered_stocks
        self.already_traded = already_traded
        self.fno_handler = fno_handler
        self.option_ctx = OptionContext()

    def _update_option_context(self):
        try:
            log("🔄 Updating option context...")

            option = self.fno_handler.handle_FnO_symbols()
            log(f"🧭 FnO handler output: {option}")

            if not option:
                log("⚠️ No option returned by FnO handler")
                return

            if isinstance(option, list):
                option_symbol = option[0]
            else:
                option_symbol = option

            log(f"🎯 Selected option symbol: {option_symbol}")

            candles = get_5min_candles(self.fyers, option_symbol)
            log(f"📊 Option candles fetched: {len(candles)}")

            if len(candles) < 2:
                log("⚠️ Not enough option candles (<2), cannot build context")
                return

            current = candles[-1]
            prev = candles[-2]

            log(
                f"🕯 Option candles → "
                f"prev(H={prev['high']}, L={prev['low']}), "
                f"current(L={current['low']})"
            )

            ts = current["day_time"]

            self.option_ctx.symbol = option_symbol
            self.option_ctx.ltp = current["low"]
            self.option_ctx.timestamp = ts
            self.option_ctx.time = datetime.now()
            self.option_ctx.SL = prev["low"]
            self.option_ctx.TG = prev["high"] + int(RR) * (prev["high"] - prev["low"])

            log(
                f"✅ Option context updated → "
                f"symbol={self.option_ctx.symbol}, "
                f"ltp={self.option_ctx.ltp}, "
                f"SL={self.option_ctx.SL}, "
                f"TG={self.option_ctx.TG}, "
                f"time={self.option_ctx.time.strftime('%H:%M:%S')}"
            )

        except Exception as e:
            log(f"❌ Error updating option context: {e}")


    def evaluate_and_trade(self):
        log(f"📐 Applying EMA strategy to {len(self.filtered_stocks)} stocks.")

        for symbol in self.filtered_stocks:
            try:
                # 1️⃣ Always refresh option context
                self._update_option_context()
                
                log(f"🔍 Evaluating index symbol: {symbol}")

                candles = get_5min_candles(self.fyers, symbol)
                log(f"📊 Index candles fetched: {len(candles)}")

                price = get_prices(candles)
                ema = calculate_ema_series(price, int(EMA_PERIOD))

                log(f"Finding the signal at EMA price = {list(ema.items())[-1][1]},time = {candles[-1]['day_time']},and index price = {list(price.items())[-1][1]}")

                signal_triggered = evaluate_trade_signal(candles, ema, symbol)

                for signal in signal_triggered:
                    
                    # Skip the trade if signal recency is more than 1
                    time = datetime.strptime(signal.get('time'), "%Y-%m-%d %H:%M")
                    signal_time = datetime.now() - time
                    signal_recency = signal_time.seconds() / 60 
                    if signal_recency < 1:
                        continue

                    log(f"🚦 Index EMA signal triggered for Time: {signal['time']}")

                    if signal['time'] == "no signal":
                        log(f"🚦 No signal as of now")
                        continue

                    if datetime.strptime(signal['time'], "%Y-%m-%d %H:%M").date() < datetime.now().date():
                        log(f"Skipping the signal from yesterday's setup which was at {signal['time']}")
                        continue

                    
                    # 🔎 Log option context snapshot BEFORE checks
                    log(
                        f"🧠 Option context snapshot → "
                        f"symbol={self.option_ctx.symbol}, "
                        f"ltp={self.option_ctx.ltp}, "
                        f"time={self.option_ctx.time}"
                    )

                    if not self.option_ctx.symbol or not self.option_ctx.ltp:
                        log("⛔ Option context NOT READY → skipping trade")
                        continue

                    age = (datetime.now() - self.option_ctx.time).seconds
                    log(f"⏱ Option context age: {age}s")

                    if age > 7:
                        log("⛔ Option price STALE it means older than 7 secs → skipping trade")
                        continue

                    unique_key = (symbol, datetime.now().strftime("%Y-%m-%d %H:%M"))
                    # if unique_key in self.already_traded:
                    #     log(f"🔁 Trade already taken for this minute → skipping, please see already taken trades: {self.already_traded} ")
                    #     continue

                    log(f"🚀 Executing FnO trade → {self.option_ctx.symbol}")

                    self.executor.place_trade(
                        symbol=self.option_ctx.symbol,
                        price=self.option_ctx.ltp,
                        sl=self.option_ctx.SL,
                        target=self.option_ctx.TG,
                        timestamp=signal['time'],
                        side= 1,
                        mode="EMA",
                        fno_lots=int(LOTS)
                    )

                    self.already_traded.add(unique_key)

            except Exception as e:
                log(f"❌ Error evaluating {self.option_ctx.symbol}: {e}")
