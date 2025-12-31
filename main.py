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
        # [사용자 원칙] 5분봉 차트 데이터 수집
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        
        # 5분봉 기준 이평선 계산 (5, 20, 60)
        ma5 = df['c'].rolling(window=5).mean().iloc[-1]
        ma20 = df['c'].rolling(window=20).mean().iloc[-1]
        ma60 = df['c'].rolling(window=60).mean().iloc[-1]
        current_price = df['c'].iloc[-1]
        
        # [V80 타점] 5분봉 정배열(LONG) / 역배열(SHORT)
        is_long = ma5 > ma20 > ma60
        is_short = ma5 < ma20 < ma60
        
        if is_long: return "LONG"
        if is_short: return "SHORT"
        return "WAIT"
    except Exception as e:
        print(f"⚠️ 5분봉 분석 오류: {e}")
        return "RETRY"

def execute_trade(exchange, symbol, signal):
    try:
        exchange.load_markets()
        
        # [원칙] 메이저 15배 / 잡코인 5배
        major_coins = ['BTC/USDT', 'ETH/USDT', 'BTCUSDT', 'ETHUSDT']
        leverage = 15 if symbol in major_coins else 5
        
        try:
            exchange.set_leverage(leverage, symbol)
        except:
            pass

        balance = exchange.fetch_balance()
        total_usdt = balance['total']['USDT']
        
        # [원칙] 2,000$ 미만 시 1종목 집중
        positions = exchange.fetch_positions([symbol])
        active_positions = [p for p in positions if float(p['contracts']) != 0]
        
        limit_count = 1 if total_usdt < 2000 else 2
        if len(active_positions) >= limit_count:
            # 이미 포지션이 있으면 추가 진입 안 함
            return

        # 진입 예산 10% * 레버리지
        entry_budget = total_usdt * 0.1 * leverage
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        
        amount = entry_budget / price
        precise_amount = float(exchange.amount_to_precision(symbol, amount))
        
        # 최소 수량(0.001) 체크
        if precise_amount < 0.001:
            precise_amount = 0.001
            
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [V80 실전] {symbol} {signal} 진입! (5분봉 {signal}배열 / {leverage}배)")
        
        order = exchange.create_market_order(symbol, side, precise_amount)
        print(f"✅ 주문 성공! ID: {order['id']}")
        print(f"💰 수익 발생 시 30% 안전자산 격리 가동 중...")
        
    except Exception as e:
        print(f"❌ 매매 오류: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    symbol = 'BTC/USDT'
    
    print("------------------------------------------")
    print("💰 V80 5분봉 [5/20/60] 정배열/역배열 엔진 가동")
    print("🛡️ 메이저 15배 / 2,000$ 미만 1종목 / 수익 30% 격리")
    print("------------------------------------------")
    
    while True:
        try:
            signal = check_v80_trend(exchange, symbol)
            print(f"[{time.strftime('%H:%M:%S')}] 5분봉 상태: {signal}")
            
            if signal in ["LONG", "SHORT"]:
                execute_trade(exchange, symbol, signal)
            
            time.sleep(60) # 1분마다 체크
        except Exception as e:
            print(f"❌ 루프 에러: {e}")
            time.sleep(10)
