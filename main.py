import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

# .env 파일 로드
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
            # USDT 선물 종목만 스캔
            if 'USDT' in symbol and 'BUSD' not in symbol:
                pct = abs(t.get('percentage', 0))
                # [사령관님 명령] 메이저/잡코인 불문 5% 이상이면 후보로 등록
                if pct >= 5.0:
                    candidates.append({'symbol': symbol, 'change': pct})
        
        # 변동률이 높은 순서대로 상위 15개 추출
        return [c['symbol'] for c in sorted(candidates, key=lambda x: x['change'], reverse=True)[:15]]
    except Exception as e:
        print(f"⚠️ 정찰 중 오류: {e}")
        return []

def check_v80_signal(exchange, symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        ma20 = df['c'].rolling(20).mean().iloc[-1]
        ma60 = df['c'].rolling(60).mean().iloc[-1]
        curr_c = df['c'].iloc[-1]

        # 20/60 정배열 + 가격이 20일선 위 (롱) / 역배열 + 가격이 20일선 아래 (숏)
        if ma20 > ma60 and curr_c > ma20: return "LONG"
        if ma20 < ma60 and curr_c < ma20: return "SHORT"
        return "WAIT"
    except: return "WAIT"

def execute_v80_trade(exchange, symbol, signal, max_slots):
    try:
        # 포지션 현황 체크
        balance = exchange.fetch_balance()
        positions = balance['info']['positions']
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        if len(active_positions) >= max_slots: return

        # 중복 종목 진입 방지
        for p in active_positions:
            if p['symbol'] == symbol.replace("/", "").replace(":USDT", ""): return

        total_usdt = float(balance['total']['USDT'])
        
        # [사령관님 원칙] 안전자산 30% 제외 후 70% 가용금액으로 운용
        tradable_balance = total_usdt * 0.7 
        entry_budget = (tradable_balance / max_slots) 
        
        price = float(exchange.fetch_ticker(symbol)['last'])
        exchange.set_leverage(5, symbol)
        
        # 수량 계산 및 주문
        amount = exchange.amount_to_precision(symbol, (entry_budget * 5) / price)
        side = 'BUY' if signal == "LONG" else 'SELL'
        
        print(f"🎯 [사격 승인] {symbol} {signal} 진입! (변동성 5% 돌파)")
        exchange.create_market_order(symbol, side, amount)

        # 트레일링 스탑 설정 (1.5%)
        ts_side = 'SELL' if side == 'BUY' else 'BUY'
        params = {'callbackRate': 1.5}
        exchange.create_order(symbol, 'TRAILING_STOP_MARKET', ts_side, amount, params=params)
        
    except Exception as e:
        print(f"❌ 매매 실행 에러: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("🏰 [V80 전종목 5% 사격 모드] 가동 시작")
    
    while True:
        try:
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            
            # 3000불 미만 1종목, 이상 2종목 자동 설정
            max_slots = 1 if total_balance < 3000 else 2
            
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            print(f"👀 정찰 중... 5% 이상 후보: {len(watch_list)}개", end='\r')

            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                if signal in ["LONG", "SHORT"]:
                    execute_v80_trade(exchange, symbol, signal, max_slots)
                    time.sleep(1) 
            
            time.sleep(10) # 10초 주기로 시장 스캔
        except Exception as e:
            print(f"❗ 시스템 루프 에러: {e}")
            time.sleep(10)
