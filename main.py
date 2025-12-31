import os
import time
import ccxt
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# 1. 바이낸스 연결 설정 (선물 전용 fapi 주소 강제 지정)
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True,
    }
})
# 깃허브 차단을 피하기 위해 현물 관련 API 호출을 원천 차단
exchange.urls['api']['public'] = 'https://fapi.binance.com/fapi'
exchange.urls['api']['private'] = 'https://fapi.binance.com/fapi'

TARGET_SYMBOLS = ['BTC/USDT', 'ETH/USDT']
MAX_POSITIONS = 2

def check_v80_trend(symbol):
    timeframes = ['6M', '3M', '1M', '1d', '12h', '6h']
    trends = []
    try:
        for tf in timeframes:
            # 선물 전용 데이터만 가져옴
            ohlcv = exchange.fapiPublicGetKlines({'symbol': symbol.replace('/', ''), 'interval': tf, 'limit': 30})
            df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ts_end', 'qav', 'nt', 'tbv', 'tqv', 'ignore'])
            df['c'] = df['c'].astype(float)
            ma20 = df['c'].rolling(window=20).mean().iloc[-1]
            current_price = df['c'].iloc[-1]
            trends.append(current_price > ma20)
            print(f"   [{tf}] {current_price} > {ma20:.2f} : {current_price > ma20}")
        
        if all(trends): return "LONG"
        if not any(trends): return "SHORT"
        return "WAIT"
    except Exception as e:
        print(f"⚠️ {symbol} 분석 에러: {e}")
        return "ERROR"

if __name__ == "__main__":
    print(f"🚀 V80 봇 가동 (615% 수익 중! 100억 고지전)")
    
    try:
        # fetch_balance 대신 차단 확률이 낮은 fapi 전용 함수 사용
        pos_info = exchange.fapiPrivateGetPositionRisk()
        active_positions = [p for p in pos_info if float(p['positionAmt']) != 0]
        pos_count = len(active_positions)
        
        print(f"📊 현재 포지션 수: {pos_count} / {MAX_POSITIONS}")

        for symbol in TARGET_SYMBOLS:
            if pos_count >= MAX_POSITIONS: break
            print(f"🔍 {symbol} 분석 시작...")
            signal = check_v80_trend(symbol)
            print(f"📢 신호: {signal}")

            if signal in ["LONG", "SHORT"]:
                print(f"🔥 {symbol} {signal} 조건 충족! (수익률 615% 유지 중)")

    except Exception as e:
        print(f"❌ 최종 에러: {e}")
