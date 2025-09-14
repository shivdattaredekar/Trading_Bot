import csv
import os
from datetime import datetime
from tradingsetup.config.settings import CAPITAL_PER_TRADE, CAPITAL
from tradingsetup.utlis.logger import log


TRADE_LOG_FILE = "trade_log.csv"

def log_trade_result(symbol, timestamp, entry_price, stop_loss, target, status, error_message=None):
    file_exists = os.path.isfile(TRADE_LOG_FILE)

    with open(TRADE_LOG_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["timestamp", "symbol", "entry_price", "stop_loss", "target", "status", "error_message"])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            entry_price,
            stop_loss,
            target,
            status,
            error_message or ""
        ])

def check_trades(symbol, file_path=TRADE_LOG_FILE):
    if not os.path.exists(file_path):
        return []

    # Read trades for the given symbol from the CSV file
    trades = []
    with open(file_path, mode="r") as file:
        reader = csv.DictReader(file)
        today = datetime.now().strftime("%Y-%m-%d")
        for row in reader:
            # Check for trade date 
            trade_date = datetime.strptime(row['timestamp'],'%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d")

            # Check for the symbol and if it is traded today and the status is successful
            if row["symbol"] == symbol and trade_date == today and row['status'] == 'success':
                trades.append(row)
    return trades

def order_quantity_calculator(CAPITAL_PER_TRADE, STOCK_PRICE, STOP_LOSS):
    try:
        capital_per_trade = float(CAPITAL_PER_TRADE)
        final_sl = STOP_LOSS - STOCK_PRICE        
        ORDER_QUANTITY = int(capital_per_trade / max(final_sl, 0.51))
        return max(ORDER_QUANTITY, 1)

    except Exception as e:
        log(f"Error in order quantity calculation: {e}")
        return 1


class TradeManager:
    """
    Manages the number of trades taken in a day.
    args:
        MAX_TRADES (int): Maximum number of trades allowed in a day.
    Returns:
        Remaining trades after each trade creation.
    """

    def __init__(self, MAX_TRADES):
        self.max_trades = MAX_TRADES
        self.trades_taken = 0

    def create_trades(self):
        self.trades_taken += 1
        log(f"Trades taken today: {self.trades_taken}")
        log(f"Remaining trades for the day: {self.max_trades - self.trades_taken}")

    def get_trades(self):
        return self.trades_taken

# If trades for any symbol are equal to two then don't trade again on that symbol 

def can_trade(symbol, file_path=TRADE_LOG_FILE):
            
    trades = check_trades(symbol, file_path)
    if len(trades) >= 2:
        return False
    return True 