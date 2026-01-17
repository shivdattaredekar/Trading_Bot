from src.tradingbot.utils.logger import log
from src.tradingbot.login.auth import get_fyers_instance, is_access_token_valid
from fyers_apiv3 import fyersModel

#fyers = get_fyers_instance()


filtered_stocks = ["NSE:NIFTY50-INDEX", "NSE:RELIANCE-EQ", "NSE:TCS-EQ"]

def handle_FnO_symbols(filtered_stocks):
    
    try:
        # The the NSE index symbol and calculate ts todays opening price
        if not filtered_stocks:
            log("No filtered stocks provided.")
            return None
        
        symbol = [symbl for symbl in filtered_stocks if "INDEX" in symbl][0]
        response = fyers.quotes({"symbols": symbol})
        
        if response.get('s') != 'ok':
            log(f"Failed to fetch quotes for {symbol}: {response}")
            return None
        
        Open_price = response['d'][0]['open_price']
        log(f"Opening price for {symbol} is {Open_price}")

        # Round off the price to the nearest 100
        rounded_price = round(Open_price / 100) * 100
        log(f"Rounded opening price for {symbol} is {rounded_price}")

        # Select the proper strike prices based on the opening price as per the expiry
        
    except Exception as e:
        log(f"Error in handling FnO symbols: {e}")
        return None


    return symbol

#print(handle_FnO_symbols(filtered_stocks))

import pandas as pd

from datetime import datetime

def extract_expiry_from_symbol(symbol_str):
    parts = symbol_str.split()

    day = parts[1]
    month = parts[2]
    year = parts[3]  # YY
    if year != 26:
        pass

    expiry_str = f"{day} {month} 20{year}"
    return datetime.strptime(expiry_str, "%d %b %Y").date()

def get_expiries(symbol="NIFTY"):
    df = pd.read_csv(
        "https://public.fyers.in/sym_details/NSE_FO.csv",
        header=None
    )

    nifty_opts = df[
        (
        (df[1].str.split().str[0] == "NIFTY") &
        (df[1].str.endswith(("CE","PE")))
    )
    ]
    
    # expiries = []
    # for opt in nifty_opts[1]:
    #     expiries.append(extract_expiry_from_symbol(opt))

    return nifty_opts[1].unique() #sorted(expiries)

expiries = get_expiries()

def get_expiry_dates(expiries):
    for exp in expiries:
        s = exp.split()
    return s

print(get_expiries())

#print(get_expiry_dates(expiries))
