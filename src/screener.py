from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import load_config
from .data.yf_data import fetch_15m_history
from .indicators import add_indicators
from .strategy.nifty_momentum import generate_signals
from .utils.timeutils import is_market_open
import pandas as pd
from .utils.debugio import write_csv, write_note, safe_name

# Debug switches
DEBUG_STEPS = True        # turn off later if you want
DEBUG_LAST_N = 120


cfg = load_config()

def screen_symbol(sym: str):
    df = fetch_15m_history(sym, cfg.screener.lookback_bars)
    if DEBUG_STEPS:
        write_csv(df, f"step_raw_{safe_name(sym)}.csv", last_n=DEBUG_LAST_N)

    if df.empty or len(df) < 50:
        return None

    df = add_indicators(
        df,
        rsi_period=cfg.strategy.rsi_period,
        macd_fast=cfg.strategy.macd_fast,
        macd_slow=cfg.strategy.macd_slow,
        macd_signal=cfg.strategy.macd_signal,
        obv_lookback=cfg.strategy.obv_lookback,
        volosc_fast=cfg.strategy.volosc_fast,
        volosc_slow=cfg.strategy.volosc_slow,
    )
    if DEBUG_STEPS:
        write_csv(df, f"step_postind_{safe_name(sym)}.csv", last_n=DEBUG_LAST_N)


    # === DEBUG: dump enriched data (with indicators) BEFORE filtering ===
    try:
        n = 1000  # how many recent rows to dump
        df.tail(n).to_csv(f"debug_{sym.replace('.', '_')}.csv")
    except Exception as _:
        pass
    # === END DEBUG ===


    # ✅ Guard: ensure indicators exist; otherwise skip this symbol
    # ✅ Guard: ensure indicators exist; otherwise skip this symbol
    required_cols = {"Close", "RSI", "MACD_HIST", "OBV_DELTA", "VO"}
    if df is None or df.empty or not required_cols.issubset(set(df.columns)):
        if DEBUG_STEPS:
            have = sorted(df.columns.tolist()) if df is not None and not df.empty else []
            write_note(sym,
                "SKIP: missing required columns or empty frame\n"
                f"have_cols={have}\n"
                f"need_cols={sorted(required_cols)}\n"
                f"raw=debug/step_raw_{safe_name(sym)}.csv\n"
                f"postind=debug/step_postind_{safe_name(sym)}.csv\n"
            )
        return None


    sig = generate_signals(
        df,
        rsi_entry=cfg.strategy.rsi_entry,
        rsi_exit=cfg.strategy.rsi_exit,
        min_volosc=cfg.strategy.min_volosc,
    )
    # Dump the signal step (booleans + inputs used to decide)
    if DEBUG_STEPS:
        sig_cols = [
            "Open", "High", "Low", "Close", "Volume",
            "RSI", "MACD_HIST", "OBV_DELTA", "VO",
            "RSI_CROSS_UP", "MACD_BULL", "OBV_POS", "VO_POS",
            "ENTRY", "RSI_CROSS_DOWN", "EXIT"
        ]
        existing = [c for c in sig_cols if c in sig.columns]
        write_csv(sig[existing], f"step_signals_{safe_name(sym)}.csv", last_n=DEBUG_LAST_N)

    last = sig.iloc[-1]

    if last.get("ENTRY", False):
        if DEBUG_STEPS:
            write_note(sym, f"MATCH: ENTRY on {sig.index[-1].isoformat()}\n"
                            f"see debug/step_signals_{safe_name(sym)}.csv")
        return {
            "symbol": sym,
            "close": float(last["Close"]),
            "rsi": float(last["RSI"]),
            "macd_hist": float(last["MACD_HIST"]),
            "obv_delta": float(last["OBV_DELTA"]),
            "vo": float(last["VO"]),
            "time": sig.index[-1].isoformat()
        }
    # no match
    if DEBUG_STEPS:
        write_note(sym, f"NO MATCH: last bar {sig.index[-1].isoformat()} did not meet ENTRY.\n"
                        f"see debug/step_signals_{safe_name(sym)}.csv")
    return None


def load_watchlist(path: str = "watchlist.csv"):
    with open(path, "r") as f:
        syms = [ln.strip() for ln in f.readlines() if ln.strip()]
    return syms

def screen_once():
    syms = load_watchlist()
    out = []
    with ThreadPoolExecutor(max_workers=cfg.screener.max_workers) as ex:
        futs = {ex.submit(screen_symbol, s): s for s in syms}
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                out.append(res)
    out.sort(key=lambda x: x["rsi"], reverse=True)
    return out

def run_screen_and_print():
    if not is_market_open():
        print("Note: market may be closed; results could be stale/incomplete.")
    rows = screen_once()
    if not rows:
        print("No symbols matched the criteria.")
        return
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
