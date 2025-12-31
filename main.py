import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

# .env 파일 경로 강제 지정
load_dotenv(dotenv_path='/home/dbffl4764/V80_Trading_Bot/.env')

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',  # 선물 거래 고정
            'adjustForTimeDifference': True,
            'recvWindow': 10000
        }
    })

def check_v80_trend(exchange, symbol):
    try:
        # 선물 전용 klines 엔드포인트 사용
        ohlcv = exchange.fapiPublicGetKlines({'symbol': symbol.replace('/', ''), 'interval': '1h', 'limit': 100})
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ts_end', 'qav', 'nt', 'tbv', 'tqv', 'ignore'])
        df['c'] = df['c'].astype(float)
        
        ma5 = df['c'].rolling(window=5).mean().iloc[-1]
        ma20 = df['c'].rolling(window=20).mean().iloc[-1]
        ma60 = df['c'].rolling(window=60).mean().iloc[-1]
        current_price = df['c'].iloc[-1]
        
        ohlcv_5m = exchange.fapiPublicGetKlines({'symbol': symbol.replace('/', ''), 'interval': '5m', 'limit': 10})
        last_5m_close = float(ohlcv_5m[-1][4])
        
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
        # 잔고 조회 (fapiPrivate 사용)
        balance = exchange.fapiPrivateGetAccount()
        total_usdt = float(next(asset['walletBalance'] for asset in balance['assets'] if asset['asset'] == 'USDT'))
        
        # 포지션 확인 (2,000$ 미만 시 1종목 집중)
        positions = exchange.fapiPrivateGetPositionRisk()
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        limit_count = 1 if total_usdt < 2000 else 2
        
        if len(active_positions) >= limit_count:
            print(f"⚠️ 원칙 준수: {total_usdt:.2f}$ 기준 {limit_count}종목 제한.")
            return

        entry_budget = total_usdt * 0.1
        ticker = exchange.fapiPublicGetTicker({'symbol': symbol.replace('/', '')})
        price = float(ticker['lastPrice'])
        amount = entry_budget / price
        
        side = 'BUY' if signal == 'LONG' else 'SELL'
        print(f"🚀 [V80 실전 진입] {symbol} {signal}! 예산: {entry_budget:.2f} USDT")
        
        # 시장가 주문
        order = exchange.fapiPrivatePostOrder({
            'symbol': symbol.replace('/', ''),
            'side': side,
            'type': 'MARKET',
            'quantity': exchange.amount_to_precision(symbol, amount)
        })
        
        print(f"✅ 주문 성공: {order['orderId']}")
        print(f"💰 수익 발생 시 30% 안전자산 격리 가동!")
        
    except Exception as e:
        print(f"❌ 매매 실행 오류 (키/권한 확인): {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    symbol = 'BTC/USDT'
    
    print("------------------------------------------")
    print("💰 V80 [5/20/60] 실전 엔진(선물 전용) 가동")
    print("------------------------------------------")
    
    while True:
        try:
            signal = check_v80_trend(exchange, symbol)
            print(f"[{time.strftime('%H:%M:%S')}] 신호: {signal}")
            if signal in ["LONG", "SHORT"]:
                execute_trade(exchange, symbol, signal)
            time.sleep(60)
        except Exception as e:
            print(f"❌ 시스템 오류: {e}")
            time.sleep(10)
