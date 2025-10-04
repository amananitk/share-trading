import pandas as pd
def generate_signals(df: pd.DataFrame, rsi_entry=45, rsi_exit=50, min_volosc=0.0) -> pd.DataFrame:
    out = df.copy()
    out['RSI_CROSS_UP'] = (out['RSI'] > rsi_entry) & (out['RSI'].shift(1) <= out['RSI'])
    out['PRICE_UP'] = ( out['Close'] >= out['Close'].shift(1) )
    out['MACD_BULL'] =  (out['MACD_HIST'] >= out['MACD_HIST'].shift(1) )
    out['OBV_POS'] = out['OBV_DELTA'] > 0
    out['VO_POS'] = ( out['VO'] > out['VO'].shift(1) )
    out['ENTRY'] = out['RSI_CROSS_UP'] & out['MACD_BULL'] & out['VO_POS'] & out['PRICE_UP']
    out['RSI_CROSS_DOWN'] = (out['RSI'] < rsi_exit) & (out['RSI'].shift(1) >= rsi_exit)
    out['EXIT'] = out['RSI_CROSS_DOWN'] | (out['MACD_HIST'] < 0)
    return out
