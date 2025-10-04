from src.config import load_config
from src.data.yf_data import fetch_15m_history
from src.indicators import add_indicators

# --- Settings ---
sym = "RELIANCE.NS"   # change this to test another symbol
last_n = 120          # how many rows to inspect/save
# -----------------

cfg = load_config()

raw = fetch_15m_history(sym, cfg.screener.lookback_bars)
print("RAW SHAPE:", raw.shape)
print(raw.tail(3))

post = add_indicators(
    raw,
    rsi_period=cfg.strategy.rsi_period,
    macd_fast=cfg.strategy.macd_fast,
    macd_slow=cfg.strategy.macd_slow,
    macd_signal=cfg.strategy.macd_signal,
    obv_lookback=cfg.strategy.obv_lookback,
    volosc_fast=cfg.strategy.volosc_fast,
    volosc_slow=cfg.strategy.volosc_slow,
)

print("POST-IND SHAPE:", post.shape)
print(post.tail(3))

# Save to CSVs for deeper look in Excel/Sheets
raw.tail(last_n).to_csv(f"probe_raw_{sym.replace('.', '_')}.csv")
post.tail(last_n).to_csv(f"probe_post_{sym.replace('.', '_')}.csv")
print(f"Saved probe_raw_{sym.replace('.', '_')}.csv and probe_post_{sym.replace('.', '_')}.csv")
