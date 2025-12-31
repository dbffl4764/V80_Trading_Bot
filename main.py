import os
import time
import ccxt
import pandas as pd
from dotenv import load_dotenv

# 1. 환경 설정 및 API 로드
load_dotenv()

# 바이낸스 선물 거래소 연결
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'options': {'defaultType': 'future'},
    'enableRateLimit': True
})

# 사용자님의 핵심 원칙 설정
TARGET_SYMBOLS = ['BTC/USDT', 'ETH/USDT']
MAX_POSITIONS = 2

# --- [전략: 6개 타임프레임 추세 일치 확인] ---
def check_v80_trend(symbol):
    # 6개월, 3개월, 1개월, 1일, 12시간, 6시간
    timeframes = ['6M', '3M', '1M', '1d', '12h', '6h']
    trends = []
    
    try:
        for tf in timeframes:
            # 이평선(20일선) 계산을 위해 30개 캔들 조회
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=30)
            df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            ma20 = df['c'].rolling(window=20).mean().iloc[-1]
            current_price = df['c'].iloc[-1]
            
            # 현재가가 이평선 위에 있는지 확인
            trends.append(current_price > ma20)
            print(f"   - {tf} 추세: {'상승' if current_price > ma20 else '하락'}")

        # 모든 타임프레임이 정렬되었는지 확인
        if all(trends): return "LONG"
        if not any(trends): return "SHORT"
        return "WAIT"
    except Exception as e:
        print(f"⚠️ 데이터 조회 실패: {e}")
        return "ERROR"

# --- [자산 관리: 수익금 안전자산 이체] ---
def manage_profit(profit_usd, profit_pct):
    if profit_usd <= 0: return
    
    # 수익률 100% 이상 시 40%, 미만 시 30% 배분 규칙
    ratio = 0.4 if profit_pct >= 1.0 else 0.3
    amount_to_move = profit_usd * ratio
    
    try:
        # 선물 계정에서 현물 계정으로 이동
        exchange.transfer("USDT", amount_to_move, "future", "spot")
        print(f"💰 [안전자산 이동] {amount_to_move:.2f} USDT 이체 완료! ({int(ratio*100)}%)")
    except Exception as e:
        print(f"❌ 이체 실패: {e}")

# --- [메인 실행부] ---
if __name__ == "__main__":
    print(f"🚀 V80 전략 봇 가동! (은퇴 목표 100억!)")
    
    try:
        # 1. 현재 열린 포지션 수 확인 (최대 2개 제한)
        balance = exchange.fetch_balance()
        positions = [p for p in balance['info']['positions'] if float(p['positionAmt']) != 0]
        pos_count = len(positions)
        print(f"📊 현재 포지션 수: {pos_count} / {MAX_POSITIONS}")

        # 2. 종목 분석 및 진입 판단
        for symbol in TARGET_SYMBOLS:
            if pos_count >= MAX_POSITIONS:
                print("🚫 이미 최대 포지션입니다. 추가 진입 불가.")
                break
                
            print(f"🔍 {symbol} 분석 시작...")
            signal = check_v80_trend(symbol)
            print(f"📢 최종 신호: {signal}")

            # 3. 진입 신호 발생 시 로직 (실제 주문 코드는 시뮬레이션 후 추가)
            if signal == "LONG":
                print(f"🔥 {symbol} 풀정배열! LONG 진입 조건 충족!")
            elif signal == "SHORT":
                print(f"🔻 {symbol} 풀역배열! SHORT 진입 조건 충족!")

        print("🏁 이번 턴 분석 완료!")

    except Exception as e:
        print(f"⚠️ 메인 루프 에러: {e}")
