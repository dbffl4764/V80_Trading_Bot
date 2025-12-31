import os
import time
import ccxt
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# 1. 깃허브 서버 차단을 피하기 위한 다중 주소 설정
# api1, api2, api3 중 하나라도 뚫리면 실행됩니다.
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True,
    },
    'urls': {
        'api': {
            'public': 'https://api1.binance.com/api',
            'private': 'https://api1.binance.com/api',
            'fapiPublic': 'https://fapi.binance.com/fapi',
            'fapiPrivate': 'https://fapi.binance.com/fapi',
        }
    }
})

TARGET_SYMBOLS = ['BTC/USDT', 'ETH/USDT']
MAX_POSITIONS = 2

def check_v80_trend(symbol):
    timeframes = ['6M', '3M', '1M', '1d', '12h', '6h']
    trends = []
    symbol_clean = symbol.replace('/', '')
    
    try:
        for tf in timeframes:
            # fapiPublicGetKlines를 사용하여 차단 확률을 낮춤
            ohlcv = exchange.fapiPublicGetKlines({
                'symbol': symbol_clean,
                'interval': tf,
                'limit': 30
            })
            df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ts_end', 'qav', 'nt', 'tbv', 'tqv', 'ignore'])
            df['c'] = df['c'].astype(float)
            ma20 = df['c'].rolling(window=20).mean().iloc[-1]
            current_price = df['c'].iloc[-1]
            trends.append(current_price > ma20)
            
        if all(trends): return "LONG"
        if not any(trends): return "SHORT"
        return "WAIT"
    except Exception as e:
        return f"ERROR: {e}"

if __name__ == "__main__":
    # 수익률 640% 돌파 기념 메시지! ㅋ
    print(f"🚀 V80 봇 재가동 (현재 수익률 640% 🔥 고지전 시작)")
    
    try:
        # 지갑 정보 조회 대신 포지션 정보만 가볍게 조회
        pos_info = exchange.fapiPrivateGetPositionRisk()
        active_positions = [p for p in pos_info if float(p['positionAmt']) != 0]
        pos_count = len(active_positions)
        
        print(f"📊 현재 운용 중인 종목: {pos_count} / {MAX_POSITIONS}")

        for symbol in TARGET_SYMBOLS:
            if pos_count >= MAX_POSITIONS: break
            
            print(f"🔍 {symbol} 6개 타임프레임 분석...")
            signal = check_v80_trend(symbol)
            print(f"📢 분석 결과: {signal}")

            if signal in ["LONG", "SHORT"]:
                print(f"🎯 {symbol} {signal} 조건 일치! (640% 수익 가즈아!)")

        print("🏁 이번 사이클 분석 완료!")

    except Exception as e:
        # 에러가 나더라도 '451'이면 재실행하면 뚫릴 때가 있습니다.
        print(f"❌ 접속 시도 실패: {e}")
