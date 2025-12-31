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

# 👑 봇의 기억 속에 있는 메이저 (무시 대상)
MAJORS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'APT/USDT',
    'BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT' # 변종 이름 대비
]

def get_dynamic_watchlist(exchange, total_balance):
    try:
        tickers = exchange.fetch_tickers()
        candidates = []
        
        for symbol, t in tickers.items():
            # 필터 완화: USDT가 포함된 모든 선물 종목 대상
            if 'USDT' in symbol:
                # 3000불 미만일 때는 메이저 이름이 포함된 종목 무시 ㅡㅡ;
                if total_balance < 3000:
                    if any(m in symbol for m in ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'LINK', 'SUI', 'APT']):
                        continue
                
                # 나머지 잡코인들은 등락률 후보에 추가
                change = abs(float(t['percentage']))
                candidates.append({'symbol': symbol, 'change': change})

        # 등락률 큰 순서대로 정렬
        sorted_list = sorted(candidates, key=lambda x: x['change'], reverse=True)
        top_10 = [m['symbol'] for m in sorted_list[:10]]

        # 자산 3000불 이상일 때만 메이저 추가
        if total_balance >= 3000:
            return list(set(MAJORS[:10] + top_10))
            
        return top_10 # 200불일 땐 무조건 이거!
    except Exception as e:
        print(f"⚠️ 리스트 갱신 에러: {e}")
        return []

def check_v80_signal(exchange, symbol):
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
    print("🏰 V80 0개 탈출 엔진 가동")
    print("------------------------------------------")
    
    while True:
        try:
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            
            # 자산 규모별 슬롯
            max_slots = 1 if total_balance < 3000 else 2

            print(f"\n[잔고: {total_balance:.1f}$] {len(watch_list)}개 종목 추적 중...")
            
            if not watch_list:
                print("👀 아직도 0개면 API 데이터를 다시 확인해야 합니다.")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                icon = "🔥"
                print(f"[{time.strftime('%H:%M:%S')}] {icon} {symbol:15} : {signal}")
                # 매매 로직은 기존 함수 활용 (execute_v80_trade)
                time.sleep(0.1)
            
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ 시스템 에러: {e}")
            time.sleep(5)
