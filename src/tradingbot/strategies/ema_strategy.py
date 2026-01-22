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
            option = self.fno_handler.handle_FnO_symbols()
            if not option:
                return

            option_symbol = option[0]
            candles = get_5min_candles(self.fyers, option_symbol)

            if len(candles) < 2:
                return
        
            current = candles[-1]
            prev = candles[-2]
            ts = current["day_time"]
            
            prev_high = prev["high"] 
            prev_low = prev["low"]
            current_low = current["low"]

            self.option_ctx.symbol = option_symbol
            self.option_ctx.ltp = current_low
            self.option_ctx.timestamp = ts
            self.option_ctx.time = datetime.now()
            self.option_ctx.SL = prev_high 
            self.option_ctx.TG =  prev_low - int(RR) * (prev_high - prev_low)

        except Exception as e:
            log(f"Error updating option context: {e}")

    def evaluate_and_trade(self):
        log(f"Applying EMA strategy to {len(self.filtered_stocks)} stocks.")

        # 1️⃣ Always refresh option context
        self._update_option_context()

        for symbol in self.filtered_stocks:
            try:
                # 2️⃣ Fetch index candles + EMA
                candles = get_5min_candles(self.fyers, symbol)
                price = get_prices(candles)
                ema = calculate_ema_series(price, int(EMA_PERIOD))

                # 3️⃣ Pure index signal
                signal_triggered = evaluate_trade_signal(candles, ema, symbol)

                if not signal_triggered:
                    continue

                # 4️⃣ Option context sanity checks
                if not self.option_ctx.symbol or not self.option_ctx.ltp:
                    log("Option context not ready, skipping trade")
                    continue

                if (datetime.now() - self.option_ctx.time).seconds > 3:
                    log("Option price stale, skipping trade")
                    continue

                unique_key = (symbol, datetime.now().strftime("%Y-%m-%d %H:%M"))
                if unique_key in self.already_traded:
                    continue

                # 5️⃣ Execute FnO trade (OPTION prices only)
                log(f"Executing FnO trade → {self.option_ctx.symbol}")

                self.executor.place_trade(
                    symbol=self.option_ctx.symbol,
                    price=self.option_ctx.ltp,
                    sl=self.option_ctx.SL,     
                    target=self.option_ctx.TG, 
                    timestamp=self.option_ctx.timestamp,
                    direction=-1,
                    strategy="EMA",
                    fno_lots=int(LOTS)
                )

                self.already_traded.add(unique_key)

            except Exception as e:
                log(f"Error evaluating {symbol}: {e}")

