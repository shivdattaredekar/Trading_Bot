from dataclasses import dataclass

@dataclass(frozen=True)
class TradeSignal:
    signal_symbol: str     # e.g. NSE:NIFTY50-INDEX
    timestamp: str
    direction: int         # -1 = SELL, +1 = BUY
    entry_price: float
    stop_loss: float
    target: float
    strategy: str          # EMA, TAMO, etc.
