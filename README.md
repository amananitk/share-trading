# Trading Agent Starter (15-min NIFTY Screener)

    This starter is a **modular trading agent** you can run locally. It scans NIFTY stocks on **15-minute candles** using **RSI, MACD, OBV, and Volume Oscillator**, with slots for paper trading and Kite Connect integration.

    > Educational use only. Markets involve risk. Test on paper first.

    ## Quick start
    ```bash
    python -m venv .venv
    # Windows: .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    pip install -r requirements.txt
    python run_screener.py            # run once in console
    streamlit run streamlit_app.py    # optional UI
    python -m src.backtest --ticker TCS.NS
