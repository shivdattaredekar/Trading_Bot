from ..utlis.logger import log
from datetime import datetime
from .ema_strategy import *


def apply_trade_logic(fyers,filtered_stocks, already_traded):
    log(f"Applying trade logic to {len(filtered_stocks)} stocks.")

    for symbol in filtered_stocks:
        log(f"[Trade Candidate: {symbol}]")
        try:
            # Fetch 5-minute candles and calculate EMA
            candles = get_5min_candles(fyers, symbol)

            # Fetch prices and calculate EMA
            price = get_prices(candles)

            # Calculate EMA
            ema = calculate_ema_series(price, 5)

            # Evaluate trade signals based on EMA strategy
            signals = evaluate_trade_signal(candles=candles, ema=ema, symbol=symbol)

            # Loop through signals and place trades
            for signal in signals:
                signal_date = datetime.strptime(signal['timestamp'], '%Y-%m-%d %H:%M').date()
                today_date = datetime.now().date()
                if signal_date < today_date:
                    log(f"Skipping signal from previous day: {signal['timestamp']}")
                    continue  # Skip signals from previous days

                unique_key = (symbol, signal["timestamp"])
                if unique_key in already_traded:
                    log(f"Skipping already traded signal: {unique_key}")
                    log(f"Skipping duplicate trade for {symbol} at {signal['timestamp']}")
                    continue  # Skip duplicate trade

                log(f"Executing trade for {symbol}: {signal}")
                # Place the trade
                place_trade(fyers,symbol, signal["entry_price"], signal["stop_loss"], signal["target"], signal['timestamp'])
                already_traded.add(unique_key)

        except Exception as e:
            log(f"Error evaluating trade for {symbol}: {e}")
            continue
