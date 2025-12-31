import os
import time
import ccxt
import pandas as pd
from dotenv import load_dotenv

# 1. 환경 변수 로드
load_dotenv()

# 2. 바이낸스 연결 설정 (IP 차단 우회 및 타임존 보정 포함)
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future', # 선물거래 기본 설정
        'adjustForTimeDifference': True, # 서버 시간 차이 자동 보정
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

# 사용자 원칙 설정
TARGET_SYMBOLS = ['BTC/USDT', 'ETH/USDT']
MAX_POSITIONS = 2

# --- [전략 로직: 6개 타임프레임 추세 확인] ---
def check_v80_trend(symbol):
    # 6개월, 3개월, 1개월, 1일, 12시간, 6시간
    timeframes = ['6M', '3M', '1M', '1d', '12h', '6h']
    trends = []
    
    try:
        for tf in timeframes:
            # 이평선 계산을 위해 캔들 30개 조회
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=30)
            df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            ma20 = df['c'].rolling(window=20).mean().iloc[-1]
            current_price = df['c'].iloc[-1]
            
            trends.append(current_price > ma20)
            print(f"   [{tf}] 현재가: {current_price} / MA20: {ma20:.2f} -> {'상승' if current_price > ma20 else '하락'}")

        if all(trends): return "LONG"
        if not any(trends): return "SHORT"
        return "WAIT"
    except Exception as e:
        print(f"⚠️ {symbol} 데이터 조회 에러: {e}")
        return "ERROR"

# --- [자산 관리: 수익금 안전자산 이체] ---
def safety_asset_management(profit_usd, profit_pct):
    if profit_usd <= 0: return
    
    # 수익률 100% 이상 시 40%, 미만 시 30% 배분
    ratio = 0.4 if profit_pct >= 1.0 else 0.3
    amount = profit_usd * ratio
    
    try:
        # 선물(Future) -> 현물(Spot) 이체
        exchange.transfer("USDT", amount, "future", "spot")
        print(f"💰 [안전지대] {amount:.2f} USDT를 현물 지갑으로 대피시켰습니다! ({int(ratio*100)}%)")
    except Exception as e:
        print(f"❌ 이체 실패 (권한 확인 필요): {e}")

# --- [실행부] ---
if __name__ == "__main__":
    print(f"🚀 V80 전략 봇 가동 시작! (목표: 100억)")
    
    try:
        # 1. 현재 포지션 수 확인 (최대 2개 제한)
        # fetch_balance 대신 fetch_positions 사용 (차단 확률 낮음)
        positions = exchange.fetch_positions()
        active_positions = [p for p in positions if float(p['contracts']) > 0]
        pos_count = len(active_positions)
        
        print(f"📊 현재 보유 종목 수: {pos_count} / {MAX_POSITIONS}")

        # 2. 종목 분석
        for symbol in TARGET_SYMBOLS:
            if pos_count >= MAX_POSITIONS:
                print(f"🚫 종목 꽉 참 ({MAX_POSITIONS}개). 분석 중단.")
                break
                
            print(f"🔍 {symbol} 정밀 분석 중...")
            signal = check_v80_trend(symbol)
            print(f"📢 분석 결과: {signal}")

            if signal == "LONG":
                print(f"🔥 {symbol} 6개 타임프레임 풀정배열! 매수 진입 시점입니다.")
            elif signal == "SHORT":
                print(f"🔻 {symbol} 6개 타임프레임 풀역배열! 매도 진입 시점입니다.")

        print("🏁 이번 사이클 분석을 마쳤습니다.")

    except Exception as e:
        print(f"❌ 최종 실행 에러: {e}")
