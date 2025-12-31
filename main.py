import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

env_path = '/home/dbffl4764/V80_Trading_Bot/.env'
load_dotenv(dotenv_path=env_path)

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

# [전략] 기회가 많은 알트코인 후보군 10선
watch_list = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'APT/USDT'
]

def check_v80_trend(exchange, symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        
        # 5분봉 5/20/60 정석 이평선
        ma5 = df['c'].rolling(window=5).mean().iloc[-1]
        ma20 = df['c'].rolling(window=20).mean().iloc[-1]
        ma60 = df['c'].rolling(window=60).mean().iloc[-1]
        
        # [원칙] 완벽한 정배열/역배열만 골라낸다
        if ma5 > ma20 > ma60: return "LONG"
        if ma5 < ma20 < ma60: return "SHORT"
        return "WAIT"
    except: return "RETRY"

def execute_trade(exchange, symbol, signal):
    try:
        # 1. 1종목 집중 원칙 (200$ 시드 보호)
        positions = exchange.fetch_positions()
        active_positions = [p for p in positions if float(p['contracts']) != 0]
        if len(active_positions) >= 1: return

        # 2. 레버리지: 메이저 15배 / 알트 5배
        major_coins = ['BTC/USDT', 'ETH/USDT']
        leverage = 15 if symbol in major_coins else 5
        exchange.load_markets()
        exchange.set_leverage(leverage, symbol)

        # 3. 진입 금액: 시드 10% (20$)
        balance = exchange.fetch_balance()
        total_usdt = balance['total']['USDT']
        entry_budget = total_usdt * 0.1 * leverage
        
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount = entry_budget / price
        precise_amount = float(exchange.amount_to_precision(symbol, amount))
        
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🎯 [V80 포착] {symbol} {signal} 진입! ({leverage}배)")
        exchange.create_market_order(symbol, side, precise_amount)
        print(f"💰 수익 발생 시 30% 안전자산 격리 대기 중... ㅡㅡ;")
        
    except Exception as e:
        print(f"❌ {symbol} 진입 에러: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print(f"🔥 V80 하이에나 엔진 가동 (알트코인 10종 스캔)")
    print(f"🛡️ 200$ 시드 1종목 집중 모드")
    print("------------------------------------------")
    
    while True:
        for symbol in watch_list:
            signal = check_v80_trend(exchange, symbol)
            # 신호가 올 때만 로그를 남겨서 깔끔하게 관리
            if signal in ["LONG", "SHORT"]:
                print(f"[{time.strftime('%H:%M:%S')}] 🚨 {symbol} 신호 포착: {signal}!")
                execute_trade(exchange, symbol, signal)
            time.sleep(1) # API 부하 방지용 1초 대기
        time.sleep(5)
