from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ExecutionInstruction:
    symbol: str
    quantity_mode: str          # "RISK_BASED" | "FIXED_LOT"
    lots: Optional[int] = None  # used only when FIXED_LOT
