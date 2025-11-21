import os

# Define project structure
project_structure = {
    "src/tradingbot": [
        "__init__.py",
        "config.py",
        "main.py",
    ],
    "src/tradingbot/strategies": [
        "__init__.py",
        "base_strategy.py",
        "ema_strategy.py",
        "tamo_strategy.py",
    ],
    "src/tradingbot/trading": [
        "__init__.py",
        "order_executor.py",
        "trade_logger.py",
        "trade_manager.py",
    ],
    "src/tradingbot/utils": [
        "__init__.py",
        "logger.py",
        "helpers.py",
    ],
    "src/tradingbot/tests": [
        "__init__.py",
        "test_trading.py",
    ],
}

# Template contents for key files
templates = {
    "src/tradingbot/__init__.py": "",
    "src/tradingbot/config.py": '''import os

CAPITAL_PER_TRADE = 10000
MAX_TRADES = 5
TRADE_LOG_FILE = "trade_logs.csv"
''',

    "src/tradingbot/main.py": '''from tradingbot.strategies.ema_strategy import EMAStrategy
from tradingbot.strategies.tamo_strategy import TAMOStrategy
from tradingbot.trading.order_executor import OrderExecutor
from tradingbot.utils.logger import log

def run():
    fyers = None  # initialize fyers client here
    log("Starting trading bot...")
    
    ema_strategy = EMAStrategy(fyers)
    tamo_strategy = TAMOStrategy(fyers)
    
    ema_strategy.run()
    tamo_strategy.run()

if __name__ == "__main__":
    run()
''',

    "src/tradingbot/strategies/base_strategy.py": '''from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, fyers):
        self.fyers = fyers

    @abstractmethod
    def evaluate_signals(self):
        pass

    @abstractmethod
    def run(self):
        pass
''',

    "src/tradingbot/strategies/ema_strategy.py": '''from tradingbot.strategies.base_strategy import BaseStrategy
from tradingbot.trading.order_executor import OrderExecutor
from tradingbot.utils.logger import log

class EMAStrategy(BaseStrategy):
    def evaluate_signals(self):
        # Add EMA crossover logic here
        return []

    def run(self):
        signals = self.evaluate_signals()
        executor = OrderExecutor(self.fyers)
        for signal in signals:
            executor.execute_trade(signal)
        log("EMA Strategy execution complete.")
''',

    "src/tradingbot/strategies/tamo_strategy.py": '''from tradingbot.strategies.base_strategy import BaseStrategy
from tradingbot.trading.order_executor import OrderExecutor
from tradingbot.utils.logger import log

class TAMOStrategy(BaseStrategy):
    def evaluate_signals(self):
        # Your single-stock TATAMOTORS logic
        return []

    def run(self):
        signals = self.evaluate_signals()
        executor = OrderExecutor(self.fyers)
        for signal in signals:
            executor.execute_trade(signal)
        log("TAMO Strategy execution complete.")
''',

    "src/tradingbot/trading/order_executor.py": '''from tradingbot.utils.logger import log
from tradingbot.config import CAPITAL_PER_TRADE

class OrderExecutor:
    def __init__(self, fyers):
        self.fyers = fyers

    def execute_trade(self, signal):
        symbol = signal.get("symbol")
        entry_price = signal.get("entry_price")
        stop_loss = signal.get("stop_loss")
        target = signal.get("target")

        log(f"Placing order for {symbol} | Entry: {entry_price} | SL: {stop_loss} | Target: {target}")
        # Integrate your fyers.place_order() logic here
''',

    "src/tradingbot/utils/logger.py": '''from datetime import datetime

def log(message: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")
''',

    "src/tradingbot/utils/helpers.py": '''def order_quantity_calculator(capital, stock_price, stop_loss):
    risk = capital * 0.01  # risk 1% per trade
    qty = int(risk / stop_loss)
    return max(qty, 1)
''',
}

# Create folders and files
for folder, files in project_structure.items():
    os.makedirs(folder, exist_ok=True)
    for file in files:
        file_path = os.path.join(folder, file)
        if file_path in templates:
            with open(file_path, "w") as f:
                f.write(templates[file_path])
        else:
            open(file_path, "a").close()

print("✅ Project structure created successfully!")
