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

# 👑 메이저 명단 (3000불 미만이면 무시 대상)
MAJORS_KEYWORDS = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'LINK', 'SUI', 'APT']

def get_dynamic_watchlist(exchange, total_balance):
    try:
        tickers = exchange.fetch_tickers()
        candidates = []
        
        for symbol, t in tickers.items():
            # 1. USDT 선물 페어만 필터링
            if 'USDT' in symbol and ":" not in symbol:
                
                # [에러 방지] 데이터가 비어있는 종목은 무시 (None 체크)
                if t['percentage'] is None or t['last'] is None:
                    continue
                
                # 2. 자산 3000불 미만일 때 메이저 무시 로직
                if total_balance < 3000:
                    if any(m in symbol for m in MAJORS_KEYWORDS):
                        continue
                
                # 3. 정상 데이터만 후보군에 추가
                try:
                    change = abs(float(t['percentage']))
                    candidates.append({'symbol': symbol, 'change': change})
                except (ValueError, TypeError):
                    continue

        # 등락률 큰 순서대로 정렬해서 10개 선정
        if not candidates:
            return []
            
        sorted_list = sorted(candidates, key=lambda x: x['change'], reverse=True)
        return [m['symbol'] for m in sorted_list[:10]]
        
    except Exception as e:
        print(f"⚠️ 리스트 갱신 에러: {e}")
        return []

def check_v80_signal(exchange, symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        if not ohlcv: return "RETRY"
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
    print("🏰 V80 0개 탈출 & 에러 수정 엔진 가동")
    print("------------------------------------------")
    
    while True:
        try:
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            
            # 메이저 무시 로직이 담긴 리스트 호출
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            
            print(f"\n[잔고: {total_balance:.1f}$] {len(watch_list)}개 종목 추적 중...")
            
            if len(watch_list) == 0:
                print("👀 데이터 긁어오는 중... 잠시만 기다려주세요.")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                print(f"[{time.strftime('%H:%M:%S')}] 🔥 {symbol:15} : {signal}")
                time.sleep(0.1)
            
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ 메인 루프 에러: {e}")
            time.sleep(5)
