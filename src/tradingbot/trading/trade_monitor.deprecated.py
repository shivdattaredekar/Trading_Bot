from src.tradingbot.utils.logger import log
from src.tradingbot.utils.helpers import save_state



# -------------------------------
# Trade Tracking Logic
# -------------------------------

def initialize_trade_data(trades:list[dict], order_tracker:list,
                    active_trades:dict, order_data:dict)-> dict:

    # Creating the trades dictionary
    for trade in trades:
        for order_id in order_tracker:
            if trade['orderNumber'] == order_id: 
                risk = abs(trade['tradePrice'] - order_data["stopPrice"])   
                active_trades.setdefault(order_tracker[order_id], {}).update({
                    "symbol": trade['symbol'],
                    "qty": trade['tradedQty'],
                    "entry_price": trade['tradePrice'],
                    "stop_price": order_data["stopPrice"],
                    "sl": round(risk, 0),
                    "side": trade["side"],
                    "achieved_rr":0,
                    "targets":{
                        f"tg_1_{i}":round(trade['tradePrice']-i*(abs(trade['tradePrice']-order_data["stopPrice"])), 0) for i in range(1,11)
                        },
                    "status":"OPEN"
                    })
                
    return active_trades

# -------------------------------
# Trade Tracker Class
# -------------------------------
class TradeTracker:
    def __init__(self, fyers, order_tracker, active_trades, symbol):
        self.fyers = fyers
        self.order_tracker = order_tracker
        self.active_trades = active_trades
        self.symbol = symbol
    
    def update_after_trade(self, trades:dict, trade_response:dict, order_data:dict):
        if not trade_response  or trade_response['code'] != 1101:
            log(f"❌ Trade error: {trade_response['message']}")
            return

        self.order_tracker.append(trade_response['id'])
        self.active_trades = initialize_trade_data(
                            trades,
                            self.order_tracker,
                            self.active_trades,
                            order_data)
        save_state(self.order_tracker, self.active_trades)
        log(f"✅ Trade successfully tracked and saved with id: {trade_response['id']}")
        return self.order_tracker, self.active_trades
    
    def update_trailing_stops(self, LTP):
        # Monitor the active trades
        for order_id, trade in list(self.active_trades.items()):
            if trade["status"] == "CLOSED":
                continue

            if not LTP:
                log(f"❌ Error fetching LTP for {self.symbol}")

            side = trade["side"]
            rr = trade["achieved_rr"]
            entry = trade["entry_price"]

            # For short trades
            if side == 1:
                if trade["stop_price"] > entry:
                    if LTP >= trade["stop_price"]:
                        trade["status"] = "CLOSED"
                        log(f"❌ Trade closed due to stop loss hit for {self.symbol} for order id :{order_id}")
                        continue

                if trade["stop_price"] < entry:
                    if LTP >= trade["stop_price"]:
                        trade["status"] = "CLOSED"
                        log(f"❌ Trade closed due to stop loss hit for {self.symbol} for order id :{order_id}")
                        continue
                        
                curr_target_key = f"tg_1_{rr+1}"
                if curr_target_key in trade["targets"]:
                    curr_target = trade["targets"][curr_target_key]

                    # check if the target hit
                    if LTP > curr_target:
                        continue

                    trade["achieved_rr"] += 1
                    trade["stop_price"] = trade["targets"][f"tg_1_{rr+1}"]
                
                    new_sp = trade["stop_price"]
                    new_target = trade["targets"][f"tg_1_{rr+2}"]
                    self.modify_sl(order_id, new_sp) 
                    log(f"🔁 Trailed SL for {self.symbol} → {new_sp} after achieving {rr+1} now targeting {rr+2} -> {new_target})")

            save_state(self.order_tracker, self.active_trades)
            
    def modify_sl(self, order_id, new_sl):
        log(f"⚙️ Modifying StopPrice for {self.symbol} with order id {order_id}")
        # Modify the trade
        data = {
            "id":order_id,
            "type":3,
            "limitPrice":0,
            "stopPrice":new_sl
            }
        
        #response = self.fyers.modify_order(data)
        response = "order was placed"
        log(f"✅ SL modified for {self.symbol} with order id {order_id}  → {new_sl}")
        log(f"Response: {response}")


