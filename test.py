from src.tradingsetup.utlis.logger import log
from datetime import datetime


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
        self.max_trades-=1
        self.trades_taken+=1
        log(f"Remaining trades for the day : {self.max_trades})")
        log(f"Trades taken today : {self.trades_taken})")

    def get_trades(self):
        return self.trades_taken

MAX_TRADES = 6

trade_manager = TradeManager(MAX_TRADES)
trade_manager.create_trades()

trade_manager.create_trades()

trade_manager.create_trades()

trade_manager.create_trades()
