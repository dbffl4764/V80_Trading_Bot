import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv()

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

def run_v80_sniper():
    exchange = get_exchange()
    print(f"\n📡 [바이낸스 정찰] {time.strftime('%H:%M:%S')} - 유격 2.5% 매복 중")

    try:
        balance = exchange.fetch_balance()
        positions = balance['info']['positions']
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        total_usdt = float(balance['total']['USDT'])
        max_slots = 1 if total_usdt < 3000 else 2

        if len(active_positions) >= max_slots:
            return

        tickers = exchange.fetch_tickers()
        candidates = []
        for symbol, t in tickers.items():
            if 'USDT' in symbol and 'BUSD' not in symbol and ':' not in symbol:
                pct = t.get('percentage', 0)
                if abs(pct) >= 5.0:
                    candidates.append({'symbol': symbol, 'change': pct})

        for item in sorted(candidates, key=lambda x: abs(x['change']), reverse=True):
            symbol = item['symbol']
            ohlcv = exchange.fetch_ohlcv(symbol, '5m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            df['c'] = df['c'].astype(float)
            
            ma20 = df['c'].rolling(20).mean().iloc[-1]
            ma60 = df['c'].rolling(60).mean().iloc[-1]
            curr_c = df['c'].iloc[-1]

            # 🔥 [사령관님 특명: 유격 2.5% 눌림목 사격]
            # 롱: 정배열 + 가격이 MA20의 2.5% 이내로 내려왔을 때
            is_long = ma20 > ma60 and (ma20 <= curr_c <= ma20 * 1.025)
            # 숏: 역배열 + 가격이 MA20의 2.5% 이내로 올라왔을 때
            is_short = ma20 < ma60 and (ma20 * 0.975 <= curr_c <= ma20)

            if is_long or is_short:
                side = "LONG" if is_long else "SHORT"
                print(f"🎯 [사격] {symbol} {side} 진입! (유격 {((curr_c/ma20)-1)*100:.2f}%)")
                execute_trade(exchange, symbol, side, 20, curr_c)
                break
    except Exception as e:
        print(f"⚠️ 바이낸스 엔진 체크: {e}")

def execute_trade(exchange, symbol, side, cost, price):
    exchange.set_leverage(5, symbol)
    amount = exchange.amount_to_precision(symbol, (cost * 5) / price)
    exchange.create_market_order(symbol, 'BUY' if side == "LONG" else 'SELL', amount)
    sl_price = price * (0.93 if side == "LONG" else 1.07)
    params = {'stopPrice': exchange.price_to_precision(symbol, sl_price)}
    exchange.create_order(symbol, 'STOP_MARKET', 'SELL' if side == "LONG" else 'BUY', amount, params=params)

if __name__ == "__main__":
    while True:
        run_v80_sniper()
        time.sleep(20)
