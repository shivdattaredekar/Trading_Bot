from tradingbot.execution.execution_instruction import ExecutionInstruction
from tradingbot.utils.logger import log

class InstrumentRouter:
    def __init__(self, fno_handler, fno_lots=1):
        self.fno_handler = fno_handler
        self.fno_lots = fno_lots

    def route(self, signal):
        # INDEX → OPTION
        if "INDEX" in signal.signal_symbol:
            options = self.fno_handler.handle_FnO_symbols()

            if not options:
                log("Router: No FnO option resolved")
                return None

            return ExecutionInstruction(
                symbol=options[0],
                quantity_mode="FIXED_LOT",
                lots=self.fno_lots
            )

        # Equity / others
        return ExecutionInstruction(
            symbol=signal.signal_symbol,
            quantity_mode="RISK_BASED",
            lots=None
        )
