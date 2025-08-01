import pandas as pd
# Step 1: Fetch all symbols from an index (large/mid/small cap)
def get_index_symbols():
    data = pd.read_excel('index_stocks.xlsx')
    return data['STOCK_FINAL'].to_list()


# Step 2: Filter stocks based on gap-up and volume criteria
def is_gap_up_and_volume_ok(fyers, symbol):
    try:
        data = fyers.quotes({"symbols": symbol})
        quote = data["d"][0]
        open_price = quote["open_price"]
        prev_close = quote["prev_close_price"]
        volume = quote["volume"]
        gap_percent = ((open_price - prev_close) / prev_close) * 100
        return gap_percent > 2 and volume > 100_000
    except Exception:
        return False

def debug_is_gap_up_and_volume(fyers, symbol):
    data = fyers.quotes({"symbols": symbol})
    quote = data["d"][0]
    open_price = quote["open_price"]
    prev_close = quote["prev_close_price"]
    volume = quote["volume"]
    gap_percent = ((open_price - prev_close) / prev_close) * 100
    return gap_percent, volume , open_price, prev_close


# Step 3: Full filter logic
def get_filtered_stocks(fyers, symbols):
    final_stocks = []
    for symbol in symbols:
        full_symbol = f"NSE:{symbol}" if not symbol.startswith("NSE:") else symbol
        if is_gap_up_and_volume_ok(fyers, full_symbol):
            final_stocks.append(full_symbol)
    return final_stocks

