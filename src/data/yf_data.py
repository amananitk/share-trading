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
    """Fetch 15 minute history for a single symbol.

    Using ``Ticker.history`` avoids a yfinance quirk where ``download`` caches the
    previous response when multiple requests are issued in quick succession. That
    manifested as every symbol receiving the exact same raw data in the screener.
    """

    lookback_bars = lookback_bars or cfg.screener.lookback_bars
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            interval="15m",
            period="60d",
            auto_adjust=False,
            actions=False,
        )
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    # Drop columns we never use (splits/dividends)
    drop_cols = [c for c in ["Dividends", "Stock Splits", "Capital Gains"] if c in df.columns]
    if drop_cols:
        df.drop(columns=drop_cols, inplace=True)
    df = _drop_ticker_level(df)
    df = _to_ist_index(df)
    df = _only_market_hours(df)
    df = df.tail(lookback_bars).copy()
    df.dropna(inplace=True)
    return df
