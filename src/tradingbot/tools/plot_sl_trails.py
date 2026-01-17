# tools/plot_sl_trails.py
import csv
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime

def load_trails(path="sl_trail_log.csv"):
    trails = defaultdict(list)
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            t = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
            trails[r["order_id"]].append((t, float(r["new_sl"])))
    return trails

def plot_trails(path="sl_trail_log.csv"):
    trails = load_trails(path)
    for order_id, data in trails.items():
        data.sort()
        xs = [d[0] for d in data]
        ys = [d[1] for d in data]
        plt.plot(xs, ys, marker='o', label=order_id)
    plt.legend()
    plt.title("SL Trail Log")
    plt.xlabel("Time")
    plt.ylabel("Stop Price")
    plt.show()

if __name__ == "__main__":
    plot_trails()
