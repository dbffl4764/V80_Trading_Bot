
import os
import time
import ccxt
import pandas as pd
from dotenv import load_dotenv

# 1. 설정 및 환경 변수 로드
load_dotenv()

exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'options': {'defaultType': 'future'},
    'enableRateLimit': True
})

# 사용자님의 핵심 원칙
TARGET_SYMBOLS = ['BTC/USDT', 'ETH/USDT']
MAX_POSITIONS = 2 

# --- [전략 로직: v80_logic 역할] ---
def check_v80_trend(symbol):
    """6개월, 3개월, 1개월, 1일, 12시간, 6시간 추세 일치 확인"""
    timeframes = ['6M', '3M', '1M', '1d', '12h', '6h']
    trends = []
    
    try:
        for tf in timeframes:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=30)
            df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            ma20 = df['c'].rolling(window=20).mean().iloc[-1]
            current_price = df['c'].iloc[-1]
            trends.append(current_price > ma20)
            
        if all(trends): return "LONG"
        if not any(trends): return "SHORT"
        return "WAIT"
    except:
        return "ERROR"

# --- [자산 관리: v80_trade 역할] ---
def get_current_positions():
    """현재 열린 포지션 개수 확인"""
    balance = exchange.fetch_balance()
    positions = balance['info']['positions']
    active_positions = [p for p in positions if float(p['positionAmt']) != 0]
    return len(active_positions)

def safety_asset_transfer(profit_usd, profit_pct):
    """수익금 30% (100% 초과시 40%) 안전자산 이체"""
    if profit_usd <= 0: return
    ratio = 0.4 if profit_pct >= 1.0 else 0.3
    amount = profit_usd * ratio
    try:
        exchange.transfer("USDT", amount, "future", "spot")
        print(f"💰 안전자산 이체 완료: {amount:.2f} USDT ({int(ratio*100)}%)")
    except Exception as e:
        print(f"❌ 이체 실패: {e}")

# --- [메인 실행 루프] ---
def run_trading_bot():
    print("🚀 V80 통합 봇 가동 (100억 프로젝트)")
    
    while True:
        try:
            pos_count = get_current_positions()
            print(f"\n[체크] 현재 포지션: {pos_count}/{MAX_POSITIONS}")

            for symbol in TARGET_SYMBOLS:
                if pos_count >= MAX_POSITIONS:
                    break
                
                signal = check_v80_trend(symbol)
                print(f"🔍 {symbol} 분석 결과: {signal}")

                if signal in ["LONG", "SHORT"]:
                    print(f"🔥 {signal} 진입 신호 발생!")
                    # 실제 주문 코드 예시: 
                    # exchange.create_market_order(symbol, signal.lower(), amount)

            time.sleep(60 * 5) # 5분마다 반복
            
        except Exception as e:
            print(f"⚠️ 실행 중 에러: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_trading_bot()
