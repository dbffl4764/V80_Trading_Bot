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

def get_dynamic_watchlist(exchange, total_balance):
    try:
        tickers = exchange.fetch_tickers()
        candidates = []
        for symbol, t in tickers.items():
            if 'USDT' in symbol and 'BUSD' not in symbol:
                # [긴급 수리] None 값이 들어올 경우를 대비해 0.0으로 기본값 설정
                raw_pct = t.get('percentage')
                pct = abs(float(raw_pct)) if raw_pct is not None else 0.0
                
                # 5% 이상 변동성 체크
                if pct >= 5.0:
                    candidates.append({'symbol': symbol, 'change': pct})
        
        return [c['symbol'] for c in sorted(candidates, key=lambda x: x['change'], reverse=True)[:15]]
    except Exception as e:
        print(f"⚠️ 정찰 중 오류 발생 (무시하고 재시도): {e}")
        return []

def check_v80_signal(exchange, symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        ma20 = df['c'].rolling(20).mean().iloc[-1]
        ma60 = df['c'].rolling(60).mean().iloc[-1]
        curr_c = df['c'].iloc[-1]

        if ma20 > ma60 and curr_c > ma20: return "LONG"
        if ma20 < ma60 and curr_c < ma20: return "SHORT"
        return "WAIT"
    except: return "WAIT"

def execute_v80_trade(exchange, symbol, signal, max_slots):
    try:
        balance = exchange.fetch_balance()
        # 바이낸스 선물 포지션 정보 추출
        pos_info = balance['info']['positions']
        active_positions = [p for p in pos_info if float(p['positionAmt']) != 0]
        
        if len(active_positions) >= max_slots: return

        # 중복 종목 체크 (심볼 포맷 보정)
        clean_symbol = symbol.replace("/", "").split(":")[0]
        for p in active_positions:
            if p['symbol'] == clean_symbol: return

        total_usdt = float(balance['total']['USDT'])
        tradable_balance = total_usdt * 0.7 
        entry_budget = (tradable_balance / max_slots) 
        
        ticker = exchange.fetch_ticker(symbol)
        price = float(ticker['last'])
        exchange.set_leverage(5, symbol)
        
        amount = exchange.amount_to_precision(symbol, (entry_budget * 5) / price)
        side = 'BUY' if signal == "LONG" else 'SELL'
        
        print(f"🎯 [사격] {symbol} {signal} 진입! (가용자산: {entry_budget:.2f}USDT)")
        exchange.create_market_order(symbol, side, amount)

        # 트레일링 스탑 설정
        ts_side = 'SELL' if side == 'BUY' else 'BUY'
        params = {'callbackRate': 1.5}
        exchange.create_order(symbol, 'TRAILING_STOP_MARKET', ts_side, amount, params=params)
        
    except Exception as e:
        print(f"❌ 매매 오류: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("🏰 [V80 무적 엔진 - 수리 완료] 5% 사격 모드 가동!")
    
    while True:
        try:
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            max_slots = 1 if total_balance < 3000 else 2
            
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            
            # 로그 출력 강화
            status_msg = f"👀 정찰 중... 후보군: {len(watch_list)}개 | 잔고: {total_balance:.2f} USDT"
            print(status_msg, end='\r')

            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                if signal in ["LONG", "SHORT"]:
                    execute_v80_trade(exchange, symbol, signal, max_slots)
                    time.sleep(1) 
            
            time.sleep(10)
        except Exception as e:
            print(f"\n❗ 시스템 에러 발생: {e}")
            time.sleep(10)
