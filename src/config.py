from pydantic import BaseModel
from typing import List
import yaml, os

class MarketCfg(BaseModel):
    start: str
    end: str
    days_open: List[int]

class ScreenerCfg(BaseModel):
    timeframe: str = "15m"
    lookback_bars: int = 300
    batch_size: int = 8
    max_workers: int = 4

class StrategyCfg(BaseModel):
    rsi_period: int = 14
    rsi_entry: float = 50
    rsi_exit: float = 50
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    obv_lookback: int = 10
    volosc_fast: int = 14
    volosc_slow: int = 28
    min_volosc: float = 0.0

class RiskCfg(BaseModel):
    stop_pct: float = 0.01
    take_pct: float = 0.02

class BacktestCfg(BaseModel):
    fee_bps: float = 5.0
    slippage_bps: float = 5.0

class KiteCfg(BaseModel):
    enabled: bool = False
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""

class BrokerCfg(BaseModel):
    kite: KiteCfg

class AppCfg(BaseModel):
    timezone: str = "Asia/Kolkata"
    market: MarketCfg
    screener: ScreenerCfg
    strategy: StrategyCfg
    risk: RiskCfg
    backtest: BacktestCfg
    broker: BrokerCfg

def load_config(path: str = "config.yaml") -> AppCfg:
    """Load YAML into AppCfg; falls back to config.example.yaml."""
    if not os.path.exists(path):
        path = "config.example.yaml"
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    return AppCfg(**raw)
