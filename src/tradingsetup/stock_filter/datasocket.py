import json
import time
import os
import pandas as pd

from fyers_apiv3.FyersWebsocket import data_ws

from tradingsetup.config.settings import CLIENT_ID, FYERS_ACCESS_TOKEN
from tradingsetup.utlis.logger import log

from threading import Event


# === Globals ===
tick_data = {}
stop_event = Event()
GAPUP_THRESHOLD = 2.0  # % gap-up required
DURATION = 10  # seconds to collect data

def get_index_symbols():
    path = os.path.join(os.getcwd(),'index_stocks.xlsx')
    data = pd.read_excel(path)
    log("Loaded symbols from Stock_list.xlsx.")
    return data['STOCK_FINAL'].to_list()

def onmessage(message):
    if isinstance(message, dict) and message.get("type") == "sf":
        symbol = message.get("symbol")
        tick_data[symbol] = message
    print("Response:", message)

def onerror(message):
    print("Error:", message)

def onclose(message):
    print("Connection closed:", message)

def export_gapup_data():
    print("Evaluating for gap-up stocks...")
    gapup_stocks = []

    for symbol, data in tick_data.items():
        open_price = data.get("open_price")
        prev_close = data.get("prev_close_price")

        if open_price and prev_close and prev_close != 0:
            gap_up_percent = ((open_price - prev_close) / prev_close) * 100

            if gap_up_percent >= GAPUP_THRESHOLD:
                gapup_stocks.append({
                    "symbol": symbol,
                    "open_price": open_price,
                    "prev_close": prev_close,
                    "gap_up_percent": round(gap_up_percent, 2),
                    "vol_traded_today": data.get("vol_traded_today"),
                    "ltp": data.get("ltp")
                })

    if gapup_stocks:
        df = pd.DataFrame(gapup_stocks)
        df.to_csv("gapup_data.csv", index=False)

        with open("GapUp_stocks.json", "w") as f:
            f.write(json.dumps([stock['symbol'] for stock in gapup_stocks]))
        
        log(f"Gap-up stocks saved to gapup_data.csv with {len(gapup_stocks)} entries.")
        print("Gap-up stocks saved to gapup_data.csv")
        print(f"Total gap-up stocks found: {len(gapup_stocks)}")
        print("Gap-up stocks saved to GapUp_stocks.json")
    else:
        print("No gap-up stocks found.")

def run_gapup_websocket(duration=DURATION):
    global fyers
    global DURATION

    DURATION = duration
    SUBSCRIBE_SYMBOLS = get_index_symbols()
    APP_ID = CLIENT_ID.split("-")[0]
    ACCESS_TOKEN = FYERS_ACCESS_TOKEN

    def onopen():
        log("WebSocket connection opened. Subscribing to data...")
        fyers.subscribe(symbols=SUBSCRIBE_SYMBOLS, data_type="SymbolUpdate")
        fyers.keep_running()
        time.sleep(DURATION)
        stop_event.set()
        fyers.close_connection()
        export_gapup_data()

    fyers = data_ws.FyersDataSocket(
        access_token=ACCESS_TOKEN,
        log_path="logs/",
        litemode=False,
        write_to_file=False,
        reconnect=False,
        on_connect=onopen,
        on_close=onclose,
        on_error=onerror,
        on_message=onmessage
    )

    fyers.connect()
