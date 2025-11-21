from datetime import datetime
from tradingbot.utils.logger import log

from tradingbot.trading.trade_logger import log_trade_result
from tradingbot.utils.helpers import (can_trade, order_quantity_calculator,
                                    validate_trade_time, calculate_sl_target,
                                    )

class TradeExecutor:
    def __init__(self, fyers, capital_per_trade, max_trades, trade_manager, trade_log_file):
        self.fyers = fyers
        self.capital = capital_per_trade
        self.max_trades = max_trades
        self.trade_manager = trade_manager
        self.trade_log_file = trade_log_file

    def prepare_order(self, symbol, qty, price, St_L, target, side):
        return {
            "symbol": symbol,
            "qty": qty,
            "type": 2,  # Market order
            "side": side, 
            "productType": "BO",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
            "stopLoss": round(St_L, 0),
            "takeProfit": round(abs(price - target), 0)
        }

    def execute_order(self, order_data):
        response = self.fyers.place_order(order_data)
        log(f"Order Response: {response}")
        return response

    def handle_order_response(self, symbol, response, price, sl, target):
        if response.get('code') == 1101:
            log_trade_result(symbol, datetime.now().strftime("%Y-%m-%d %H:%M"), price, sl, target, "success")
            self.trade_manager.create_trades()
            log(f"✅ Order placed successfully for {symbol}")
        else:
            log_trade_result(symbol, datetime.now().strftime("%Y-%m-%d %H:%M"), price, sl, target, "failed")
            log(f"❌ Order failed for {symbol}: {response}")

    def place_trade(self, symbol, price, sl, target, timestamp, side=-1):
        try:
            if not validate_trade_time(timestamp):
                log(f"Trade for {symbol} is outside trading window. Skipping.")
                return

            St_L, target = calculate_sl_target(price, sl, target)
            qty = order_quantity_calculator(self.capital, STOCK_PRICE=price, STOP_LOSS=St_L)
            log(f"after SL after filtering the final SL:{St_L}, final_target:{target}, qty:{qty}")

            if not can_trade(symbol, self.trade_log_file):
                log(f"{symbol} already traded today. Skipping.")
                return

            if self.trade_manager.get_trades() >= int(self.max_trades):
                log("Max trades reached. Skipping new orders.")
                return

            order_data = self.prepare_order(symbol, qty, price, St_L, target, side)
            response = self.execute_order(order_data)
            self.handle_order_response(symbol, response, price, sl, target)

        except Exception as e:
            log(f"Error placing trade for {symbol}: {e}")
            log_trade_result(symbol, datetime.now().strftime("%Y-%m-%d %H:%M"), price, sl, target, "failed", str(e))

    def place_TAMO_trade(self, symbol, price, sl, target, timestamp, side):
        try:
            if not validate_trade_time(timestamp):
                log(f"Trade for {symbol} is outside trading window. Skipping.")
                return

            St_L, target = calculate_sl_target(price, sl, target)
            qty = order_quantity_calculator(self.capital, STOCK_PRICE=price, STOP_LOSS=St_L)

            order_data = self.prepare_order(symbol, qty, price, St_L, target, side)
            response = self.execute_order(order_data)
            self.handle_order_response(symbol, response, price, St_L, target)

        except Exception as e:
            log(f"Error placing trade for {symbol}: {e}")
            log_trade_result(symbol, datetime.now().strftime("%Y-%m-%d %H:%M"), price, sl, target, "failed", str(e))

