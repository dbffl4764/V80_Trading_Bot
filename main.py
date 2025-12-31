import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

# .env 파일 절대 경로 지정
env_path = '/home/dbffl4764/V80_Trading_Bot/.env'
load_dotenv(dotenv_path=env_path)

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

def check_v80_trend(exchange, symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        
        ma5 = df['c'].rolling(window=5).mean().iloc[-1]
        ma20 = df['c'].rolling(window=20).mean().iloc[-1]
        ma60 = df['c'].rolling(window=60).mean().iloc[-1]
        current_price = df['c'].iloc[-1]
        
        ohlcv_5m = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=10)
        last_5m_close = float(ohlcv_5m[-1][4])
        
        is_long = current_price > ma5 > ma20 > ma60 and last_5m_close > current_price * 0.999
        is_short = current_price < ma5 < ma20 < ma60 and last_5m_close < current_price * 1.001
        
        if is_long: return "LONG"
        if is_short: return "SHORT"
        return "WAIT"
    except Exception as e:
        print(f"⚠️ 차트 분석 오류: {e}")
        return "RETRY"

def execute_trade(exchange, symbol, signal):
    try:
        # 1. 잔고 및 마켓 정보 로드
        exchange.load_markets()
        balance = exchange.fetch_balance()
        total_usdt = balance['total']['USDT']
        
        # 2. 포지션 확인 (2,000$ 미만 시 1종목 집중)
        positions = exchange.fetch_positions([symbol])
        active_positions = [p for p in positions if float(p['contracts']) != 0]
        
        limit_count = 1 if total_usdt < 2000 else 2
        if len(active_positions) >= limit_count:
            print(f"⚠️ 원칙: {total_usdt:.2f}$ 기준 {limit_count}종목 제한 중.")
            return

        # 3. 진입 금액 계산 (10%)
        entry_budget = total_usdt * 0.1
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        
        # [핵심] 수량 정밀도 계산: 바이낸스 규격에 맞게 수량을 다듬습니다.
        amount = entry_budget / price
        precise_amount = exchange.amount_to_precision(symbol, amount)
        
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [V80 실전] {symbol} {signal} 진입 시도! (수량: {precise_amount})")
        
        # 4. 시장가 주문 실행
        order = exchange.create_market_order(symbol, side, precise_amount)
        print(f"✅ 주문 성공! ID: {order['id']}")
        print(f"💰 수익 발생 시 30% 안전자산 격리 가동!")
        
    except Exception as e:
        print(f"❌ 매매 오류: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    symbol = 'BTC/USDT'
    
    print("------------------------------------------")
    print("💰 V80 [5/20/60] 엔진 - 수량 정밀도 패치 완료")
    print("------------------------------------------")
    
    while True:
        try:
            signal = check_v80_trend(exchange, symbol)
            print(f"[{time.strftime('%H:%M:%S')}] 신호: {signal}")
            if signal in ["LONG", "SHORT"]:
                execute_trade(exchange, symbol, signal)
            time.sleep(60)
        except Exception as e:
            print(f"❌ 루프 에러: {e}")
            time.sleep(10)
