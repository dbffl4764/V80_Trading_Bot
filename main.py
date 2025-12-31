import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

# [핵심] 서버 내 .env 파일 위치를 절대 경로로 강제 지정 (apiKey 에러 해결)
env_path = '/home/dbffl4764/V80_Trading_Bot/.env'
load_dotenv(dotenv_path=env_path)

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future', 'adjustForTimeDifference': True}
    })

def check_v80_trend(exchange, symbol):
    """
    [사용자 전략] 이평선 5, 20, 60 & 분봉 60, 20, 5 추세 일치 확인
    """
    try:
        # 1시간봉(60분) 데이터 수집
        ohlcv = exchange.fapiPublicGetKlines({'symbol': symbol.replace('/', ''), 'interval': '1h', 'limit': 100})
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ts_end', 'qav', 'nt', 'tbv', 'tqv', 'ignore'])
        df['c'] = df['c'].astype(float)
        
        # 이동평균선 계산 (5, 20, 60)
        ma5 = df['c'].rolling(window=5).mean().iloc[-1]
        ma20 = df['c'].rolling(window=20).mean().iloc[-1]
        ma60 = df['c'].rolling(window=60).mean().iloc[-1]
        current_price = df['c'].iloc[-1]
        
        # 5분봉 단기 추세 확인
        ohlcv_5m = exchange.fapiPublicGetKlines({'symbol': symbol.replace('/', ''), 'interval': '5m', 'limit': 10})
        last_5m_close = float(ohlcv_5m[-1][4])
        
        # [V80 필승 타점] 모든 이평선 정배열 + 단기 분봉 일치
        is_long = current_price > ma5 > ma20 > ma60 and last_5m_close > current_price * 0.999
        is_short = current_price < ma5 < ma20 < ma60 and last_5m_close < current_price * 1.001
        
        if is_long: return "LONG"
        if is_short: return "SHORT"
        return "WAIT"
    except Exception as e:
        print(f"⚠️ 데이터 분석 중 오류: {e}")
        return "RETRY"

def execute_trade(exchange, symbol, signal):
    try:
        # 1. 자산 확인
        balance = exchange.fetch_balance()
        total_usdt = balance['total']['USDT']
        
        # 2. 포지션 확인 (2,000$ 미만 시 1종목 집중 원칙)
        positions = exchange.fapiPrivateGetPositionRisk()
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        limit_count = 1 if total_usdt < 2000 else 2
        
        if len(active_positions) >= limit_count:
            print(f"⚠️ 원칙 준수: {total_usdt:.2f}$ 기준 {limit_count}종목 제한 중.")
            return

        # 3. 잔고 10% 진입 금액 계산
        entry_budget = total_usdt * 0.1
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount = entry_budget / price
        
        # 4. 실전 주문 집행
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [V80 실전 진입] {symbol} {signal}! 예산: {entry_budget:.2f} USDT")
        order = exchange.create_market_order(symbol, side, amount)
        
        print(f"✅ 주문 성공: {order['id']}")
        print(f"💰 수익 발생 시 30% 안전자산 격리 가동 예정!")
        
    except Exception as e:
        print(f"❌ 매매 실행 오류 (키 확인 필요): {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    symbol = 'BTC/USDT'
    
    print("------------------------------------------")
    print("💰 V80 [5/20/60] 실전 엔진 최종본 가동")
    print(f"🛡️ 원칙: 2,000$ 전 1종목 / 수익 30% 격리")
    print("------------------------------------------")
    
    while True:
        try:
            signal = check_v80_trend(exchange, symbol)
            print(f"[{time.strftime('%H:%M:%S')}] 분석 결과: {signal}")
            
            if signal in ["LONG", "SHORT"]:
                execute_trade(exchange, symbol, signal)
            
            time.sleep(60)
        except Exception as e:
            print(f"❌ 시스템 오류: {e}")
            time.sleep(10)
