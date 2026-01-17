from datetime import datetime
from tradingbot.utils.logger import log
from tradingbot.utils.helpers import (
    get_5min_candles,
    get_prices,
    calculate_ema_series,
    evaluate_trade_signal
)
from tradingbot.strategies.base_strategy import BaseStrategy
from tradingbot.config import EMA_PERIOD


class EMAStrategy(BaseStrategy):
    def __init__(self, fyers, executor, filtered_stocks, already_traded, router):
        super().__init__(fyers, executor)
        self.filtered_stocks = filtered_stocks
        self.already_traded = already_traded
        self.router = router

    def evaluate_and_trade(self):
        log(f"Applying EMA strategy to {len(self.filtered_stocks)} stocks.")
        for symbol in self.filtered_stocks:
            try:
                candles = get_5min_candles(self.fyers, symbol)
                price = get_prices(candles)
                ema = calculate_ema_series(price, int(EMA_PERIOD))
                signals = evaluate_trade_signal(candles, ema, symbol)

                for signal in signals:
                    if datetime.strptime(signal['timestamp'], '%Y-%m-%d %H:%M').date() < datetime.now().date():
                        continue

                    unique_key = (signal.signal_symbol, signal.timestamp)
                    if unique_key in self.already_traded:
                        continue
                    
                    trade_symbol = self.router.route(signal)
                    if trade_symbol is None:
                        continue
            
                    log(f"Routing {signal.signal_symbol} → {trade_symbol}")

                    log(f"Executing trade for {symbol}: {signal}")
                    self.executor.place_trade(
                        trade_symbol,
                        signal.entry_price,
                        signal.stop_loss,
                        signal.target,
                        signal.timestamp,
                        signal.direction,
                        signal.strategy
                    )
                    self.already_traded.add(unique_key)

            except Exception as e:
                log(f"Error evaluating {symbol}: {e}")
