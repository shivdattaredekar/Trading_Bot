from datetime import datetime, time, timedelta
from tradingbot.utils.logger import log

class SingleStockStrategy:
    def __init__(self, symbol, RR, fyers):
        self.symbol = symbol 
        self.RR = int(RR)
        self.fyers = fyers
        

    def _get_candles(self):
        log(f"Fetching candles for {self.symbol}...")
        
        data = self.fyers.history({
                    "symbol": self.symbol,
                    "resolution": "5",
                    "date_format": "1",
                    "range_from": datetime.now().date(),
                    "range_to": datetime.now().date(),
                    "cont_flag": "1"
                })
        candle = data.get("candles", [])
            
        # Optional: Convert timestamp to readable format for inspection
        candles = []

        for c in candle:
            dt = datetime.fromtimestamp(c[0])
            if dt.time() > time(9, 55):
                candles.append({
                    "daytime": datetime.fromtimestamp(c[0]).strftime('%Y-%m-%d %H:%M'),
                    "day_time": dt.strftime("%H:%M"),
                    "open": c[1],
                    "high": c[2],
                    "low": c[3],
                    "close": c[4],
                    "volume": c[5]
                })

        return candles

    def _get_trigger_candle(self, candles):
            
        for candle in candles:
            if candle["day_time"] == "10:00":
                return candle
        return None

    def evaluate_trade_signal(self):
        self.candles = self._get_candles()
        if not self.candles:
            log(f"No candles fetched for {self.symbol}. Skipping evaluation.")
            return None, None
        
        trigger_candle = self._get_trigger_candle(self.candles)
        
        if not trigger_candle:
            log("No 10.00 AM trigger candle found.")
            return None, None
        
        trigger_high = trigger_candle["high"]
        trigger_low = trigger_candle["low"]
        trigger_range = trigger_high - trigger_low

        log(f"Trigger candle found for {self.symbol} - High: {trigger_high}, Low: {trigger_low}")

        try:
            for candle in self.candles: 
                if candle["day_time"] < "10:00":
                    continue

                log(f"Candle {candle['day_time']} evaluated. High: {candle['high']}, Low: {candle['low']}")

                # Buy condition
                if candle["high"] > trigger_high:
                    side = 1
                    log("Trade signal evaluated as Buy.")
                    signal = {
                        "timestamp": candle["daytime"],
                        "action": "BUY",
                        "entry_price": trigger_high,
                        "stop_loss": trigger_low,
                        "target": round(trigger_high + self.RR * trigger_range, 0)
                    }
                    log(f"Buy Triggered for {self.symbol} SETUP at {candle['daytime']}")
                    return signal, side
                
                # Sell condition
                elif candle["low"] < trigger_low:
                    side = -1
                    log("Trade signal evaluated as Sell.")
                    signal = {
                        "timestamp": candle["daytime"],
                        "action": "SELL",
                        "entry_price": trigger_low,
                        "stop_loss": trigger_high,
                        "target": round(trigger_low - self.RR * trigger_range, 0)
                    }
                    log(f"Sell Triggered for {self.symbol} SETUP at {candle['daytime']}")
                    return signal, side
                
                else:
                    log(f"No breakout yet. Watching further candles...")
            return None, None

        except Exception as e:
            log(f"Trade signal evaluated as invalid due to: {e}")
            return None, None
