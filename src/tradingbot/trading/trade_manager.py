import os
import json
from tradingbot.utils.logger import log


class TradeManager:
    """
    Manages the number of trades taken in a day.
    args:
        MAX_TRADES (int): Maximum number of trades allowed in a day.
    Returns:
        Remaining trades after each trade creation.
    """

    def __init__(self, MAX_TRADES:int, trade_file:str):
        self.max_trades = MAX_TRADES
        self.trade_file = trade_file
        
        # Initialize file if not exists
        if not os.path.exists(trade_file):
            with open(trade_file, 'w') as f:
                json.dump({'trades_taken': 0}, f)
        
        # Load trades from file    
        with open(self.trade_file,'r') as f:
            data = json.load(f)
        
        self.trades_taken = data.get('trades_taken', 0)

    def create_trades(self):
        # Increment counter
        self.trades_taken += 1

        # Log status
        log(f"Trades taken today: {self.trades_taken}")
        log(f"Remaining trades for the day: {self.max_trades - self.trades_taken}")
        
        # Save back to the file
        with open(self.trade_file, 'w') as f:
            json.dump({'trades_taken':self.trades_taken}, f)        

    def get_trades(self):
        return self.trades_taken
