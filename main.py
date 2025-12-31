import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path='/home/dbffl4764/V80_Trading_Bot/.env')

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

def check_v80_strict_signal(exchange, symbol):
    """
    사용자 원칙: 크로스 후 3~5봉 지점 (엄격 모드)
    5/20/60 선이 정렬되고, 선들 사이의 간격이 벌어지기 시작할 때만 진입
    """
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        
        # 이평선 계산
        ma5 = df['c'].rolling(5).mean()
        ma20 = df['c'].rolling(20).mean()
        ma60 = df['c'].rolling(60).mean()
        
        curr_ma5, prev_ma5 = ma5.iloc[-1], ma5.iloc[-2]
        curr_ma20, prev_ma20 = ma20.iloc[-1], ma20.iloc[-2]
        curr_ma60, prev_ma60 = ma60.iloc[-1], ma60.iloc[-2]

        # 1. 롱(Long) 엄격 조건: 5 > 20 > 60 정배열 + 이격 확대
        if curr_ma5 > curr_ma20 > curr_ma60:
            # 이전 봉에서도 정배열이었는지 확인 (최소 3봉 이상 유지 확인용)
            if ma5.iloc[-3] > ma20.iloc[-3] > ma60.iloc[-3]:
                # 현재 선들 사이의 간격이 이전보다 벌어지고 있는지 확인 (추세 강화)
                if (curr_ma5 - curr_ma20) > (prev_ma5 - prev_ma20):
                    return "LONG"
        
        # 2. 숏(Short) 엄격 조건: 5 < 20 < 60 역배열 + 이격 확대
        if curr_ma5 < curr_ma20 < curr_ma60:
            if ma5.iloc[-3] < ma20.iloc[-3] < ma60.iloc[-3]:
                if (curr_ma20 - curr_ma5) > (prev_ma20 - prev_ma5):
                    return "SHORT"
                    
        return "WAIT"
    except:
        return "RETRY"

# ... (기존 get_dynamic_watchlist 및 execute_v80_trade 함수와 동일하게 유지)

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🏰 V80 [3~5봉 엄격 확인] 모드 가동")
    print("💡 크로스 후 추세 확정 시에만 진입합니다.")
    print("------------------------------------------")
    
    # 메인 루프에서 check_v80_strict_signal을 호출하도록 설정
    # (나머지 실행 로직은 동일)
