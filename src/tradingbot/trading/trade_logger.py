import csv
import os
import json
from datetime import datetime, time
from tradingbot.config import CAPITAL_PER_TRADE, CAPITAL
from tradingbot.utils.logger import log


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

