from src.tradingbot.utils.logger import log
import pandas as pd
from datetime import datetime


class FnOStockHandler:
    def __init__(self,
                fyers, 
                filtered_stocks:list,
                symbol:str ="NIFTY",
                side:str ="PE"):
        self.fyers = fyers
        self.symbol = symbol
        self.side = side 
        self.filtered_stocks = filtered_stocks

    def get_strike_prices(self):
        df = pd.read_csv(
            "https://public.fyers.in/sym_details/NSE_FO.csv",
            header=None
        )

        nifty_opts = df[
            (
            (df[1].str.split().str[0] == self.symbol) &
            (df[1].str.endswith(("CE","PE")))
        )
        ]
        
        return nifty_opts[1].unique() 

    def get_SP_dates(self, rounded_price:int):
        SP = self.get_strike_prices()    

        today  = datetime.today().date()
        current_month = today.strftime("%b")
        current_year = today.strftime("%y")
        current_day = today.day

        filtered_SP = []    
        for exp in SP:
            year = exp.split()[1]
            price = int(exp.split()[4])
            price_side = exp.endswith(self.side)
            expiry_day = int(exp.split()[3])
            expiry_month = exp.split()[2]

            if (year == current_year) and (price == rounded_price) and (price_side) and (abs(expiry_day - current_day) <=7) and (expiry_month == current_month):
                filtered_SP.append(exp)

        return filtered_SP

    def handle_FnO_symbols(self):
        
        try:
            # The the NSE index symbol and calculate ts todays opening price
            if not self.filtered_stocks:
                log("No filtered stocks provided.")
                return None
            
            symbol = [symbl for symbl in self.filtered_stocks if "INDEX" in symbl][0]
            response = self.fyers.quotes({"symbols": symbol})
            
            if response.get('s') != 'ok':
                log(f"Failed to fetch quotes for {symbol}: {response}")
                return None
            
            open_price = response['d'][0]['v']['open_price']
            log(f"Opening price for {symbol} is {open_price}")

            # Round off the price to the nearest 100
            rounded_price = round(open_price / 100) * 100
            log(f"Rounded opening price for {symbol} is {rounded_price}")

            # Select the proper strike prices based on the opening price as per the expiry
            option = self.get_SP_dates(rounded_price)

            return option[0]
            
        except Exception as e:
            log(f"Error in handling FnO symbols: {e}")
            return None

