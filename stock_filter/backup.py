from datetime import datetime, timedelta
from ..utlis.logger import log
import time
import statistics
import pandas as pd
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json


"""
# ---------- Batch Gap Up % Fetch ----------
def batch_gap_up(fyers, symbols, rate_limiter):
    
    "Batch quotes() for up to 50 symbols.Returns dict: {symbol: gap_up_percentage or -1}"
    
    result = {}
    if not symbols:
        return result
    rate_limiter.wait()
    try:
        payload = {"symbols": ",".join(symbols)}
        resp = fyers.quotes(payload)
        for item in resp.get("d", []):
            sym = item.get("n")
            v = item.get("v", {})
            if sym and v.get("open_price") is not None and v.get("prev_close_price") is not None:
                result[sym] = ((v["open_price"] - v["prev_close_price"]) / v["prev_close_price"]) * 100
            else:
                result[sym] = -1
    except Exception as e:
        print(f"❌ Error in batch quotes: {e}")
        for s in symbols:
            result[s] = -1
    return result


"""

def _get_avg_volume_blocking(fyers, symbol, days, rate_limiter):
    if rate_limiter:
        rate_limiter.wait()
    payload = {
        "symbol": symbol,
        "resolution": "D", "date_format": "0",
        "range_from": str(int((datetime.now() - timedelta(days=days)).timestamp())),
        "range_to": str(int(time.time())), "cont_flag": "1"
    }
    try:
        resp = fyers.history(payload)
        candles = resp.get("candles", [])
        if candles:
            volumes = [c[5] for c in candles]
            return symbol, round(statistics.mean(volumes))
        return symbol, -1
    except Exception as e:
        print(f"❌ Error history() for {symbol}: {e}")
        return symbol, -1
    
async def get_avg_volume_async(fyers, symbols, days, rate_limiter, max_workers=10):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = [
            loop.run_in_executor(
                executor,
                _get_avg_volume_blocking,
                fyers, symbol, days, rate_limiter
            )
            for symbol in symbols
        ]
        results = await asyncio.gather(*tasks)
    return dict(results)


"""
async def get_gapup_stocks_async(fyers, symbol_list, rate_limiter, gap_threshold=2):
    final_gapup = []
    gap_data = []

    for i in range(0, len(symbol_list), 50):
        batch = symbol_list[i:i + 50]
        gap_map = batch_gap_up(fyers, batch, rate_limiter)

        for sym in batch:
            gap = gap_map.get(sym, -1)
            if gap > gap_threshold:
                final_gapup.append(sym)
            gap_data.append({'Stock': sym, 'Gap Up %': gap})

    pd.DataFrame(gap_data).to_csv('gapup_results.csv', index=False)
    with open("filtered_stocks.json", "w") as f:
        json.dump(final_gapup, f)
    return final_gapup
"""


async def final_filter_with_volume(fyers, symbols, rate_limiter, days=60, vol_threshold=100000):
    volume_map = await get_avg_volume_async(fyers, symbols, days, rate_limiter)

    final = []
    records = []

    log(f"{'Symbol':<20}{'Gap Up %':<12}{'Avg Volume':<12}{'Status'}")
    print("-" * 60)

    for sym in symbols:
        gap = "--"
        vol = volume_map.get(sym, -1)
        status = "Included" if vol > vol_threshold else "Excluded"
        if status == "Included":
            final.append(sym)
            log(f"Included {sym} | Volume: {vol}")
        else:
            log(f"Excluded {sym} | Volume: {vol}")
        print(f"{sym:<20}{gap:<12}{vol:<12}{status}")
        records.append({'Stock': sym, 'Avg Volume': vol, 'Status': status})

    pd.DataFrame(records).to_csv('filtered_stocks.csv', index=False)
    return final

