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

def get_realtime_watchlist(exchange):
    """자산 3000불 미만일 때: 오직 시가 5000불 미만 잡코인 중 등락률 TOP 10만!"""
    try:
        tickers = exchange.fetch_tickers()
        candidates = []
        
        for symbol, t in tickers.items():
            # USDT 선물 페어만, 파생상품 제외
            if not symbol.endswith('/USDT') or ":" in symbol: continue
            
            price = float(t['last'])
            change = abs(float(t['percentage'])) # 변동폭(절대값)
            
            # 사용자 원칙: 5000불 넘는 메이저는 3000불 전까지 무시! ㅡㅡ;
            if price < 5000:
                candidates.append({'symbol': symbol, 'change': change})

        # 등락률(절대값) 큰 순서대로 정렬
        sorted_list = sorted(candidates, key=lambda x: x['change'], reverse=True)
        
        # 상위 10개만 뽑기
        top_10 = [m['symbol'] for m in sorted_list[:10]]
        return top_10
    except Exception as e:
        print(f"⚠️ 리스트 가져오기 에러: {e}")
        return []

def check_v80_signal(exchange, symbol):
    """5분봉 5/20/60 정배열 분석"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        ma5 = df['c'].rolling(5).mean().iloc[-1]
        ma20 = df['c'].rolling(20).mean().iloc[-1]
        ma60 = df['c'].rolling(60).mean().iloc[-1]
        
        if ma5 > ma20 > ma60: return "LONG"
        if ma5 < ma20 < ma60: return "SHORT"
        return "WAIT"
    except: return "RETRY"

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🔥 V80 [잡코인 전용] 스나이퍼 모드 재가동")
    print("🚫 3000불 미만: 메이저 코인 전면 차단")
    print("------------------------------------------")
    
    while True:
        try:
            # 잔고 확인 (3000불 체크용)
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            
            # 3000불 미만이면 무조건 잡코인 10개만 사냥!
            if total_balance < 3000:
                watch_list = get_realtime_watchlist(exchange)
                max_slots = 1
            else:
                # 3000불 넘으면 그때 메이저 추가 (추후 확장 가능)
                watch_list = get_realtime_watchlist(exchange) # 일단 잡코인 유지
                max_slots = 2 

            print(f"\n[잔고: {total_balance:.1f}$] {len(watch_list)}개 잡코인 추적 중...")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                print(f"[{time.strftime('%H:%M:%S')}] 🔥 {symbol:12} : {signal}")
                
                # 매매 로직은 기존 원칙 유지 (1종목 등)
                # execute_v80_trade(exchange, symbol, signal, max_slots)
                
                time.sleep(0.5)
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ 루프 에러: {e}")
            time.sleep(10)
