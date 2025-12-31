import pandas as pd

def check_trend(exchange, symbol):
    timeframes = ['6M', '3M', '1M', '1d', '12h', '6h']
    trends = []
    for tf in timeframes:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=30)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        ma20 = df['c'].rolling(window=20).mean().iloc[-1]
        trends.append(df['c'].iloc[-1] > ma20)
    
    if all(trends): return "LONG"
    if not any(trends): return "SHORT"
    return "WAIT"
