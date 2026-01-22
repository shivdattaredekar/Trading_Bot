from src.tradingbot.utils.logger import log
import pandas as pd
from datetime import datetime
from typing import List
from tradingbot.config import FNO_ATM_MODE


class FnOStockHandler:
    def __init__(self, fyers, filtered_stocks, symbol="NIFTY", side="PE"):
        self.fyers = fyers
        self.symbol = symbol
        self.side = side
        self.filtered_stocks = filtered_stocks

        self.cached_option = None
        self.cached_strike = None
        self.cached_date = datetime.today().date()

        self._fo_df = None   # CSV cache

    # ---------------------------
    # CSV loader (once per day)
    # ---------------------------
    def _load_fo_csv(self):
        if self._fo_df is None:
            self._fo_df = pd.read_csv(
                "https://public.fyers.in/sym_details/NSE_FO.csv",
                header=None
            )
        return self._fo_df

    # ---------------------------
    # Fetch index price
    # ---------------------------
    def _get_index_price(self, mode="OPEN"):
        index_symbol = [s for s in self.filtered_stocks if "INDEX" in s][0]
        resp = self.fyers.quotes({"symbols": index_symbol})

        if resp.get("s") != "ok":
            return None

        v = resp["d"][0]["v"]
        return v["open_price"] if mode == "OPEN" else v["lp"]

    # ---------------------------
    # Resolve option symbol
    # ---------------------------
    def _resolve_option(self, rounded_price: int) -> str | None:

        df = self._load_fo_csv()

        today = datetime.today().date()
        cur_month = today.strftime("%b")
        cur_year = today.strftime("%y")
        cur_day = today.day

        opts = df[
            (df[1].str.startswith(self.symbol)) &
            (df[1].str.endswith(self.side))
        ][1]

        valid = []
        for sym in opts:
            parts = sym.split()
            year, month, day, strike = parts[1], parts[2], int(parts[3]), int(parts[4])

            if (
                year == cur_year and
                month == cur_month and
                strike == rounded_price and
                abs(day - cur_day) <= 7
            ):
                valid.append((day, sym))

        if not valid:
            return None

        # nearest expiry
        valid.sort(key=lambda x: x[0])
        return valid[0][1]

    # ---------------------------
    # PUBLIC API
    # ---------------------------
    def handle_FnO_symbols(self) -> List[str] | None:

        today = datetime.today().date()

        # -------- CACHE (OPEN mode only) --------
        if (
            FNO_ATM_MODE == "OPEN" and
            self.cached_option and
            self.cached_date == today
        ):
            return [self.cached_option]

        # -------- FETCH INDEX PRICE --------
        index_price = self._get_index_price(FNO_ATM_MODE)
        if index_price is None:
            log("FnO: index price fetch failed")
            return None

        rounded_price = round(index_price / 100) * 100

        # -------- RESOLVE OPTION --------
        option = self._resolve_option(rounded_price)
        if not option:
            log(f"FnO: no option found for strike {rounded_price}")
            return None

        # -------- CACHE ONLY FOR OPEN MODE --------
        if FNO_ATM_MODE == "OPEN":
            self.cached_option = option
            self.cached_date = today

        log(f"FnO [{FNO_ATM_MODE}] resolved: {option}")
        return [option]
