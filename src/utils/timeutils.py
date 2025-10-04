from datetime import datetime, time
import pytz
from ..config import load_config
cfg = load_config()
def now_ist():
    tz = pytz.timezone(cfg.timezone)
    return datetime.now(tz)
def is_market_open(dt=None):
    dt = dt or now_ist()
    dow = dt.isoweekday()
    if dow not in cfg.market.days_open:
        return False
    t = dt.time()
    start = time.fromisoformat(cfg.market.start)
    end = time.fromisoformat(cfg.market.end)
    return start <= t <= end
