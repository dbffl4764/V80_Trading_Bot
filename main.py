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

# 3000불 미만일 때 무시할 메이저 키워드
MAJORS_KEYWORDS = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'LINK', 'SUI', 'APT']

def get_dynamic_watchlist(exchange, total_balance):
    try:
        tickers = exchange.fetch_tickers()
        volatile_candidates = []
        
        for symbol, t in tickers.items():
            # 1. USDT 선물 페어인지 확인
            if '/USDT' in symbol:
                if t.get('percentage') is None: continue
                
                change_percent = float(t['percentage']) # 등락률
                
                # [핵심] ±15% 이상 변동성이 있는 놈들만 필터링 ㅡㅡ;ㅋ
                if abs(change_percent) >= 15:
                    
                    # 2. 3000불 미만일 때 메이저 무시 로직
                    if total_balance < 3000:
                        if any(m in symbol for m in MAJORS_KEYWORDS):
                            continue
                    
                    volatile_candidates.append({
                        'symbol': symbol, 
                        'change': change_percent
                    })

        # 등락률 큰 순서대로 정렬 (폭등주/폭락주 순)
        sorted_list = sorted(volatile_candidates, key=lambda x: abs(x['change']), reverse=True)
        
        # 15% 넘는 놈들 다 가져오거나, 너무 많으면 상위 15개만
        return [m['symbol'] for m in sorted_list[:15]]
        
    except Exception as e:
        print(f"⚠️ 리스트 생성 중 에러: {e}")
        return []

# check_v80_signal 및 execute_v80_trade 함수는 기존 로직 유지

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🚀 V80 [±15% 변동성 스나이퍼] 모드 가동")
    print("💡 등락률 15% 미만은 쳐다보지도 않음 ㅡㅡ;ㅋ")
    print("------------------------------------------")
    
    while True:
        try:
            balance = exchange.fetch_balance()
            total_balance = balance.get('total', {}).get('USDT', 0)
            
            # 15% 필터링된 리스트 가져오기
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            
            print(f"\n[잔고: {total_balance:.1f}$] 변동성 15% 이상 종목 {len(watch_list)}개 발견")
            
            if not watch_list:
                print("👀 현재 시장에 15% 이상 움직이는 미친 코인이 없네요. 대기 중...")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                print(f"[{time.strftime('%H:%M:%S')}] 🔥 {symbol:15} : {signal}")
                time.sleep(0.5)
            
            time.sleep(10) # 15% 코인이 적을 땐 좀 천천히 돌아도 됨
        except Exception as e:
            print(f"⚠️ 에러: {e}")
            time.sleep(5)
