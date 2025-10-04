import yfinance as yf
import pandas as pd
from zoneinfo import ZoneInfo
from ..config import load_config

cfg = load_config()
IST = ZoneInfo(cfg.timezone)  # "Asia/Kolkata"

def _to_ist_index(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if getattr(df.index, "tz", None) is None:
        df.index = df.index.tz_localize("UTC").tz_convert(IST)
    else:
        df.index = df.index.tz_convert(IST)
    return df

def _drop_ticker_level(df: pd.DataFrame) -> pd.DataFrame:
    """If yfinance returns MultiIndex (Price, Ticker), drop the ticker level to keep only OHLCV."""
    if df is None or df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex) and df.columns.nlevels > 1:
        # drop the last level (usually the ticker) → leaves 'Open','High','Low','Close','Adj Close','Volume'
        df.columns = df.columns.droplevel(-1)
    # Normalize column names
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
    return df.rename(columns=rename_map)

def _only_market_hours(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    return df.between_time(cfg.market.start, cfg.market.end, inclusive="both")

def fetch_15m_history(symbol: str, lookback_bars: int | None = None) -> pd.DataFrame:
    lookback_bars = lookback_bars or cfg.screener.lookback_bars
    df = yf.download(
        symbol,
        interval="15m",
        period="60d",
        progress=False,
        auto_adjust=False,
        group_by="column",     # ← prevents per-ticker grouping
        threads=False          # sanity; single symbol anyway
    )
    if df is None or df.empty:
        return pd.DataFrame()
    df = _drop_ticker_level(df)
    df = _to_ist_index(df)
    df = _only_market_hours(df)
    df = df.tail(lookback_bars).copy()
    df.dropna(inplace=True)
    return df
