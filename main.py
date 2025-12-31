import ccxt
import pandas as pd
import os
from v80_logic import check_v80_strategy
from v80_trade import connect_binance, get_current_balance

def run_v80_system():
    # 깃허브 시크릿에서 키 가져오기
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    bot = connect_binance(api_key, secret_key)
    
    # 1. 데이터 수집
    ohlcv = bot.fetch_ohlcv("BTC/USDT", timeframe='1d', limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # 2. 사령관님 전략 실행 (340% 수익 모드)
    current_profit = 340 
    is_safe, ratio, ma20 = check_v80_strategy(df, current_profit)
    price = df['close'].iloc[-1]
    
    print(f"📢 [V80 리포트] 현재가: {price} | 20일선: {ma20:.2f}")
    
    if not is_safe:
        print("🚨 경보: 20일선 이탈! 안전자산 이체 로직 가동 준비.")
        # 여기에 안전자산 이체 함수 실행 가능
    else:
        print("✅ 상태: 20일선 위 순항 중. 1000%까지 홀딩 유지.")

if __name__ == "__main__":
    run_v80_system()
