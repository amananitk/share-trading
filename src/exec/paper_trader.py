"""
Very simple paper-trading loop for the 15m screener strategy.

What it does
- Every 5 minutes:
  - Loads your watchlist
  - Fetches latest data, computes indicators, and checks ENTRY/EXIT
  - Buys 1 unit on ENTRY if not already in a position
  - Sells entire position on EXIT
  - Appends fills to paper_trades.csv and updates paper_positions.csv

Notes
- This is educational. It approximates fills at the latest Close.
- Run it while your venv is active.
"""

import time
import os
import csv
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..config import load_config
from ..data.yf_data import fetch_15m_history
from ..indicators import add_indicators
from ..strategy.nifty_momentum import generate_signals

CFG = load_config()
DATA_DIR = Path(".")
TRADES_CSV = DATA_DIR / "paper_trades.csv"
POS_CSV = DATA_DIR / "paper_positions.csv"
WATCHLIST = "watchlist.csv"

SLEEP_SECONDS = 300  # 5 minutes

def utcnow_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def ensure_csv_headers():
    if not TRADES_CSV.exists():
        with open(TRADES_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["time_utc","symbol","side","qty","price"])
    if not POS_CSV.exists():
        with open(POS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["symbol","qty","avg_price"])

def read_positions() -> dict:
    if not POS_CSV.exists():
        return {}
    df = pd.read_csv(POS_CSV)
    pos = {}
    for _, r in df.iterrows():
        pos[r["symbol"]] = {"qty": float(r["qty"]), "avg_price": float(r["avg_price"])}
    return pos

def write_positions(positions: dict):
    rows = [{"symbol": s, "qty": p["qty"], "avg_price": p["avg_price"]} for s, p in positions.items() if p["qty"] != 0]
    df = pd.DataFrame(rows)
    df.to_csv(POS_CSV, index=False)

def append_trade(symbol: str, side: str, qty: float, price: float):
    with open(TRADES_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([utcnow_iso(), symbol, side, qty, price])

def load_watchlist(path=WATCHLIST) -> list[str]:
    with open(path, "r") as f:
        return [ln.strip() for ln in f if ln.strip()]

def latest_signal_row(symbol: str):
    df = fetch_15m_history(symbol, lookback_bars=CFG.screener.lookback_bars)
    if df.empty or len(df) < 50:
        return None
    df = add_indicators(
        df,
        rsi_period=CFG.strategy.rsi_period,
        macd_fast=CFG.strategy.macd_fast,
        macd_slow=CFG.strategy.macd_slow,
        macd_signal=CFG.strategy.macd_signal,
        obv_lookback=CFG.strategy.obv_lookback,
        volosc_fast=CFG.strategy.volosc_fast,
        volosc_slow=CFG.strategy.volosc_slow,
    )
    sig = generate_signals(
        df,
        rsi_entry=CFG.strategy.rsi_entry,
        rsi_exit=CFG.strategy.rsi_exit,
        min_volosc=CFG.strategy.min_volosc,
    )
    return sig.iloc[-1] if len(sig) else None

def run_once():
    ensure_csv_headers()
    positions = read_positions()
    syms = load_watchlist()

    entries, exits = [], []

    for s in syms:
        last = latest_signal_row(s)
        if last is None:
            continue

        price = float(last["Close"])
        # ENTRY: if strategy says ENTRY and not already long
        if bool(last.get("ENTRY", False)):
            if s not in positions or positions[s]["qty"] == 0:
                # Buy 1 unit
                qty = 1.0
                positions[s] = {"qty": qty, "avg_price": price}
                append_trade(s, "BUY", qty, price)
                entries.append((s, price))
        # EXIT: if in a position and strategy says EXIT
        if bool(last.get("EXIT", False)):
            if s in positions and positions[s]["qty"] > 0:
                qty = positions[s]["qty"]
                append_trade(s, "SELL", qty, price)
                positions[s] = {"qty": 0.0, "avg_price": 0.0}
                exits.append((s, price))

    write_positions(positions)

    # Print a quick summary
    if entries or exits:
        print(f"[{utcnow_iso()}] Entries: {entries} | Exits: {exits}")
    else:
        print(f"[{utcnow_iso()}] No actions.")

def main():
    print("Paper trader started. Ctrl+C to stop.")
    while True:
        try:
            run_once()
            time.sleep(SLEEP_SECONDS)
        except KeyboardInterrupt:
            print("\nPaper trader stopped by user.")
            break
        except Exception as exc:
            # Don't crash the loop on transient API/IO errors
            print(f"[{utcnow_iso()}] ERROR: {exc}")
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
