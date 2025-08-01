from datetime import datetime, timedelta
from ..utlis.logger import log
import time
import statistics
import pandas as pd
import asyncio
from concurrent.futures import ThreadPoolExecutor



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

