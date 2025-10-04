import os
from pathlib import Path

DEBUG_DIR = Path("debug")   # all debug files go here
DEBUG_DIR.mkdir(exist_ok=True)

def safe_name(sym: str) -> str:
    return sym.replace(".", "_").replace("/", "_")

def write_csv(df, filename: str, last_n: int = 120):
    try:
        if df is None or df.empty:
            # Still write an empty file to indicate we got here
            (DEBUG_DIR / filename).write_text("")
            return
        df.tail(last_n).to_csv(DEBUG_DIR / filename)
    except Exception:
        pass

def write_note(sym: str, text: str):
    try:
        (DEBUG_DIR / f"note_{safe_name(sym)}.txt").write_text(text)
    except Exception:
        pass
