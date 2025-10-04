import pandas as pd
import numpy as np
import pandas_ta as ta

def _flatten_yf(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex) and out.columns.nlevels > 1:
        out.columns = out.columns.droplevel(-1)
    rename_map = {
        "Adj Close": "AdjClose",
        "adjclose": "AdjClose",
        "adj close": "AdjClose",
        "close": "Close",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "volume": "Volume",
    }
    out = out.rename(columns=rename_map)
    return out


def _coerce_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure OHLCV are numeric Series; sort index; drop dupes/NaNs."""
    out = _flatten_yf(df)

    # If MultiIndex remains, drop the last level (ticker)
    if isinstance(out.columns, pd.MultiIndex) and out.columns.nlevels > 1:
        out.columns = out.columns.droplevel(-1)

    # Keep only typical columns if present
    keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume", "AdjClose"] if c in out.columns]
    out = out[keep_cols].copy()

    # Drop duplicate column names (keep the first)
    if out.columns.duplicated().any():
        out = out.loc[:, ~out.columns.duplicated()].copy()

    # Sort index and drop duplicate index rows
    out = out[~out.index.duplicated(keep="last")].sort_index()

    # Coerce each to numeric, reduce any accidental 2-D to 1-D
    for c in out.columns:
        s = out[c]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        out[c] = pd.to_numeric(s, errors="coerce")

    # Must have Close
    if "Close" not in out.columns:
        return pd.DataFrame()

    out = out.dropna(subset=["Close"])
    return out

def _fallback_macd(close: pd.Series, fast=12, slow=26, signal=9):
    """MACD via EMAs (no pandas_ta dependency)."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    return macd_line, macd_signal, macd_hist

def _as_series(x, index):
    """Ensure 1-D Series aligned to index (never a DataFrame)."""
    if isinstance(x, pd.DataFrame):
        x = x.iloc[:, 0]
    # Convert to Series and align to our DataFrame index
    x = pd.Series(x, index=index)
    return x


def _volume_oscillator(volume: pd.Series, fast=14, slow=28) -> pd.Series:
    """Percentage Volume Oscillator (PVO-style): (EMA_fast - EMA_slow) / EMA_slow * 100."""
    vfast = volume.ewm(span=fast, adjust=False).mean()
    vslow = volume.ewm(span=slow, adjust=False).mean()
    vo = (vfast - vslow) / vslow.replace(0, np.nan) * 100.0
    return vo

def add_indicators(
    df: pd.DataFrame,
    rsi_period=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    obv_lookback=10,
    volosc_fast=14,
    volosc_slow=28,
    min_required_rows: int | None = None,
    diagnostics: bool = False,
) -> pd.DataFrame:
    """
    Adds RSI, MACD (line/signal/hist), OBV + lookback delta, and Volume Oscillator.
    Robust to partial NaNs; uses built-in implementations when pandas_ta pieces are missing.
    Returns empty DataFrame only if we truly can't compute required fields.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = _coerce_ohlcv(df)

    # Minimum bars needed (soft)
    min_needed = max(
        rsi_period + 5,
        macd_slow + macd_signal + 5,
        obv_lookback + 2,
        volosc_slow + 2,
        60,  # general floor
    )
    if min_required_rows is not None:
        min_needed = max(min_needed, int(min_required_rows))
    if len(out) < min_needed:
        if diagnostics:
            print(f"[ind] insufficient rows: have={len(out)} need>={min_needed}")
        return pd.DataFrame()

    # RSI
    out["RSI"] = ta.rsi(out["Close"], length=rsi_period)

    # MACD: try pandas_ta, else fallback
   # --- MACD: try pandas_ta, else fallback; force all outputs to Series ---
    macd = ta.macd(out["Close"], fast=macd_fast, slow=macd_slow, signal=macd_signal)
    
    if macd is not None and isinstance(macd, pd.DataFrame):
        macd_line_col = f"MACD_{macd_fast}_{macd_slow}_{macd_signal}"
        macd_sig_col  = f"MACDs_{macd_fast}_{macd_slow}_{macd_signal}"
        macd_hist_col = f"MACDh_{macd_fast}_{macd_slow}_{macd_signal}"
        if all(c in macd.columns for c in [macd_line_col, macd_sig_col, macd_hist_col]):
            out["MACD"]        = _as_series(macd[macd_line_col], out.index)
            out["MACD_SIGNAL"] = _as_series(macd[macd_sig_col],  out.index)
            out["MACD_HIST"]   = _as_series(macd[macd_hist_col], out.index)
        else:
            # Unexpected column names -> use our EMA fallback
            macd_line, macd_sig, macd_hist = _fallback_macd(
                _as_series(out["Close"], out.index), macd_fast, macd_slow, macd_signal
            )
            out["MACD"]        = _as_series(macd_line, out.index)
            out["MACD_SIGNAL"] = _as_series(macd_sig,  out.index)
            out["MACD_HIST"]   = _as_series(macd_hist, out.index)
    else:
        # pandas_ta.macd returned None -> use fallback
        macd_line, macd_sig, macd_hist = _fallback_macd(
            _as_series(out["Close"], out.index), macd_fast, macd_slow, macd_signal
        )
        out["MACD"]        = _as_series(macd_line, out.index)
        out["MACD_SIGNAL"] = _as_series(macd_sig,  out.index)
        out["MACD_HIST"]   = _as_series(macd_hist, out.index)
    # --- end MACD block ---

    # OBV and its lookback delta
    out["OBV"] = ta.obv(out["Close"], out["Volume"])
    out["OBV_DELTA"] = out["OBV"].diff(obv_lookback)

    # Volume Oscillator: our own implementation (no pandas_ta.vo)
    out["VO"] = _volume_oscillator(out["Volume"], fast=volosc_fast, slow=volosc_slow)

    # Drop rows where any required field is NaN at the end
    required = ["RSI", "MACD_HIST", "OBV_DELTA", "VO", "Close"]
    out = out.dropna(subset=required)

    if diagnostics:
        counts = {c: int(out[c].notna().sum()) for c in required}
        print(f"[ind] counts: {counts} (len={len(out)})")

    return out
