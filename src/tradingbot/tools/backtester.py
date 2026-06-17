import pandas as pd
from datetime import datetime, timedelta
import time

from tradingbot.login.auth import get_fyers_instance
from tradingbot.utils.logger import log

fyers = get_fyers_instance()

def fetch_5min_data(
    symbol: str,
    months: int = 5,
    save_path: str = "historical_5min.csv"
):
    """
    Fetch last `months` months of 5-min candle data from Fyers
    and save to CSV.
    """

    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)

    all_candles = []

    curr_start = start_date

    while curr_start < end_date:
        curr_end = min(curr_start + timedelta(days=90), end_date)

        log(f"📥 Fetching {symbol} | {curr_start.date()} → {curr_end.date()}")

        data = {
            "symbol": symbol,
            "resolution": "5",
            "date_format": "1",
            "range_from": curr_start.strftime("%Y-%m-%d"),
            "range_to": curr_end.strftime("%Y-%m-%d"),
            "cont_flag": "1"
        }

        resp = fyers.history(data=data)

        if resp.get("code") != 200 or "candles" not in resp:
            log(f"❌ Failed: {resp}")
            break

        for candle in resp["candles"]:
            all_candles.append({
                "timestamp": datetime.fromtimestamp(candle[0]),
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
                "volume": candle[5]
            })

        curr_start = curr_end + timedelta(days=1)

        time.sleep(0.3)  # avoid rate limit

    if not all_candles:
        raise ValueError("No candle data fetched from Fyers")

    df = pd.DataFrame(all_candles)
    df = df.sort_values("timestamp").reset_index(drop=True)

    df.to_csv(save_path, index=False)

    log(f"✅ Saved {len(df)} candles to {save_path}")
    return df


if __name__ == "__main__":
    fetch_5min_data(
        symbol="NSE:BPCL-EQ",
        months=5,
        save_path="EMA_5min_BPCL.csv"
    )
