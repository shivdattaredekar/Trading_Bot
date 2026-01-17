# src/tradingbot/tools/log_analyzer.py

import csv
from collections import defaultdict
from datetime import datetime
import argparse

def parse_sl_trail(path="sl_trail_log.csv"):
    trails = defaultdict(list)
    try:
        with open(path) as f:
            reader = csv.DictReader(f)
            for r in reader:
                t = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
                trails[r["order_id"]].append((t, float(r["new_sl"])))
    except FileNotFoundError:
        print("No sl_trail_log.csv found.")
    return trails

def summarize_trails(path="sl_trail_log.csv"):
    trails = parse_sl_trail(path)
    for oid, records in trails.items():
        records.sort()
        print(f"Order {oid}: {len(records)} SL updates. First: {records[0]} Last: {records[-1]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sl", default="sl_trail_log.csv")
    args = parser.parse_args()
    summarize_trails(args.sl)
