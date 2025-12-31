import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path='/home/dbffl4764/V80_Trading_Bot/.env')

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

# 100억 고지전용 진짜 야생마 리스트
watch_list = [
    'BTC/USDT', 'ETH/USDT', 'PNUT/USDT', 'NEIRO/USDT', 'ACT/USDT',
    'SUI/USDT', 'SOL/USDT', 'PEPE/USDT', 'WIF/USDT', 'ORDI/USDT'
]

def check_volatility_and_signal(exchange, symbol):
    try:
        # 1. 변동성 필터 (24시간 고가/저가 기준 5% 미만 컷!)
        ticker = exchange.fetch_ticker(symbol)
        vola = ((float(ticker['high']) - float(ticker['low'])) / float(ticker['low'])) * 100
        
        if vola < 5.0:
            return f"🗑️ {vola:.1f}% (버림)", None

        # 2. 변동성 통과 시 V80 5분봉 분석
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        ma5 = df['c'].rolling(5).mean().iloc[-1]
        ma20 = df['c'].rolling(20).mean().iloc[-1]
        ma60 = df['c'].rolling(60).mean().iloc[-1]
        
        if ma5 > ma20 > ma60: return f"🔥 {vola:.1f}%", "LONG"
        if ma5 < ma20 < ma60: return f"❄️ {vola:.1f}%", "SHORT"
        return f"👀 {vola:.1f}%", "WAIT"
    except:
        return "⚠️ 에러", "RETRY"

def execute_v80_trade(exchange, symbol, signal):
    try:
        # 1종목 집중 원칙
        positions = exchange.fetch_positions()
        if any(float(p['contracts']) != 0 for p in positions): return

        # 레버리지: 메이저 15 / 알트 5
        leverage = 15 if symbol in ['BTC/USDT', 'ETH/USDT'] else 5
        exchange.set_leverage(leverage, symbol)

        # 진입 예산: 200$의 10% (20$)
        balance = exchange.fetch_balance()
        entry_usdt = balance['total']['USDT'] * 0.1 * leverage
        
        price = exchange.fetch_ticker(symbol)['last']
        amount = exchange.amount_to_precision(symbol, entry_usdt / price)
        
        side = 'buy' if signal == "LONG" else 'sell'
        print(f"🚀 [V80 실전] {symbol} {signal} 진입! ({leverage}배)")
        exchange.create_market_order(symbol, side, amount)
        print(f"💰 수익 발생 시 30% 안전자산 격리 대기!")
        
    except Exception as e:
        print(f"❌ 진입 실패: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🛡️ V80 하드코어 필터 엔진 가동 (5% 미만 컷)")
    print("------------------------------------------")
    
    while True:
        for symbol in watch_list:
            status, signal = check_volatility_and_signal(exchange, symbol)
            print(f"[{time.strftime('%H:%M:%S')}] {symbol}: {status} -> {signal if signal else 'PASS'}")
            
            if signal in ["LONG", "SHORT"]:
                execute_v80_trade(exchange, symbol, signal)
            time.sleep(1)
        time.sleep(5)
