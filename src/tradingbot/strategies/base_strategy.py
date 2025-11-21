from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, fyers, executor):
        self.fyers = fyers
        self.executor = executor

    @abstractmethod
    def evaluate_and_trade(self):
        pass
