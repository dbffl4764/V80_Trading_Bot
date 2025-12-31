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

MAJORS_KEYWORDS = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'LINK', 'SUI', 'APT']

def get_dynamic_watchlist(exchange, total_balance):
    try:
        tickers = exchange.fetch_tickers()
        volatile_candidates = []
        for symbol, t in tickers.items():
            if 'USDT' in symbol and ":" not in symbol:
                pct = t.get('percentage', 0)
                low = t.get('low', 0)
                last = t.get('last', 0)
                low_to_last_pct = ((last - low) / low * 100) if low > 0 else 0
                max_change = max(abs(pct), low_to_last_pct)
                if max_change >= 15:
                    if total_balance < 3000 and any(m in symbol for m in MAJORS_KEYWORDS): continue
                    volatile_candidates.append({'symbol': symbol, 'change': max_change})
        return [m['symbol'] for m in sorted(volatile_candidates, key=lambda x: x['change'], reverse=True)[:15]]
    except: return []

def check_v80_signal(exchange, symbol):
    """정배열/역배열 20일선 기준 버티기 로직"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        ma20 = df['c'].rolling(20).mean()
        ma60 = df['c'].rolling(60).mean()

        curr_c = df['c'].iloc[-1]
        curr_ma20 = ma20.iloc[-1]
        curr_ma60 = ma60.iloc[-1]

        # 롱: 20 > 60 유지 및 캔들이 20일선 위 (눌림목 버티기)
        if curr_ma20 > curr_ma60 and curr_c > curr_ma20: return "LONG"
        # 숏: 20 < 60 유지 및 캔들이 20일선 아래 (반등 버티기)
        if curr_ma20 < curr_ma60 and curr_c < curr_ma20: return "SHORT"
        return "WAIT"
    except: return "RETRY"

def execute_v80_trade(exchange, symbol, signal, max_slots):
    try:
        pos_info = exchange.fetch_positions()
        active_positions = [p for p in pos_info if float(p.get('contracts', 0)) != 0]
        if len(active_positions) >= max_slots: return

        # 중복 진입 방지
        for pos in active_positions:
            if pos['symbol'] == symbol: return

        balance = exchange.fetch_balance()
        total_usdt = balance['total']['USDT']
        ticker = exchange.fetch_ticker(symbol)
        price = float(ticker['last'])
        
        exchange.set_leverage(5, symbol)
        entry_budget = (total_usdt * 0.1) * 5
        amount = exchange.amount_to_precision(symbol, entry_budget / price)
        
        # 시장가 진입
        side = 'buy' if signal == 'LONG' else 'sell'
        exchange.create_market_order(symbol, side, amount)
        print(f"🚀 [진입] {symbol} {signal} | 20일선 기준 추격 시작!")

        # 트레일링 스탑 설정 (고점/저점 대비 1.5% 되돌림 시 자동 익절)
        # 바이낸스 선물 API 특성상 별도 파라미터 전달
        params = {'activationPrice': price * (1.02 if signal == 'LONG' else 0.98), 'callbackRate': 1.5}
        ts_side = 'sell' if signal == 'LONG' else 'buy'
        exchange.create_order(symbol, 'TRAILING_STOP_MARKET', ts_side, amount, params=params)
        print(f"🛡️ [스탑로스] {symbol} 트레일링 스탑(1.5%) 작동!")

    except Exception as e: print(f"❌ 매매 에러: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🏰 V80 [추세 버티기 + 추격 익절] 가동")
    print("------------------------------------------")
    while True:
        try:
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            max_slots = 1 if total_balance < 3000 else 2
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                if signal in ["LONG", "SHORT"]:
                    execute_v80_trade(exchange, symbol, signal, max_slots)
                time.sleep(0.1)
            time.sleep(10)
        except: time.sleep(10)
