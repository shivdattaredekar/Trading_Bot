import csv
import os
from datetime import datetime

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
        for row in reader:
            if row["symbol"] == symbol:
                trades.append(row)

    return trades


# If trades for any suymbol are equal to two then don't trade again on that symbol
def can_trade(symbol, file_path=TRADE_LOG_FILE):
    trades = check_trades(symbol, file_path)
    if len(trades) >= 2:
        return False
    return True 