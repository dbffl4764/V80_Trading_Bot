import pandas as pd

def check_trend(exchange, symbol):
    # 사용자님의 6개 기준 타임프레임
    timeframes = ['6M', '3M', '1M', '1d', '12h', '6h']
    trends = []
    
    for tf in timeframes:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=30)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        ma20 = df['c'].rolling(window=20).mean().iloc[-1]
        current_price = df['c'].iloc[-1]
        trends.append(current_price > ma20)

    if all(trends): return "LONG"   # 6개 모두 상승 시
    if not any(trends): return "SHORT" # 6개 모두 하락 시
    return "WAIT"
