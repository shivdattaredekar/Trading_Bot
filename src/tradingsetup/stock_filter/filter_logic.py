import statistics
import pandas as pd
from datetime import datetime, timedelta
from tradingsetup.utlis.logger import log


def get_avg_volume(fyers, symbol, days=60):
    """
    Get the average traded volume for a stock in the last `days`.
    """
    # Use yesterday as the end date to avoid missing today's candle
    end_time = datetime.now() - timedelta(days=2)

    payload = {
        "symbol": symbol,
        "resolution": "D",
        "date_format": "0",
        "range_from": str(int((datetime.now() - timedelta(days=days+1)).timestamp())),
        "range_to": str(int(end_time.timestamp())),
        "cont_flag": "1"
    }


    try:
        resp = fyers.history(payload)
        candles = resp.get("candles", [])
        if candles:
            volumes = [c[5] for c in candles]
            return symbol, round(statistics.mean(volumes))
        return symbol, -1
    except Exception as e:
        log(f"Error history() for {symbol}: {e}")
        return symbol, -1


def final_filter_with_volume(fyers, symbols, days=60, vol_threshold=50000):
    """
    Filter stocks based on average traded volume.
    """
    volume_map = {}
    for sym in symbols:
        sym, vol = get_avg_volume(fyers, sym, days)
        volume_map[sym] = vol

    final = []
    records = []

    log(f"{'Symbol':<20}{'Gap Up %':<12}{'Avg Volume':<12}{'Status'}")
    print("-" * 60)

    for sym in symbols:
        gap = "--"  # gap% calculation not included in your snippet
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
    


