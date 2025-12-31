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

# 무시할 메이저 키워드
MAJORS_KEYWORDS = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'LINK', 'SUI', 'APT']

def get_dynamic_watchlist(exchange, total_balance):
    try:
        # fetch_tickers가 간혹 누락될 수 있어 fetch_markets 데이터와 조합
        tickers = exchange.fetch_tickers()
        volatile_candidates = []
        
        for symbol, t in tickers.items():
            # 필터링 조건 대폭 완화: USDT가 포함된 모든 시장 데이터 확인
            if 'USDT' in symbol:
                # 데이터가 None인 경우 건너뜀
                pct = t.get('percentage')
                if pct is None: continue
                
                change_percent = float(pct)
                
                # 🔥 15% 이상 변동성 체크
                if abs(change_percent) >= 15:
                    # 자산 3000불 미만 시 메이저 무시
                    if total_balance < 3000:
                        # 종목명에 메이저 키워드가 포함되면 무시
                        if any(m in symbol for m in MAJORS_KEYWORDS):
                            continue
                    
                    volatile_candidates.append({'symbol': symbol, 'change': change_percent})

        # 변동성 큰 순서대로 정렬
        sorted_list = sorted(volatile_candidates, key=lambda x: abs(x['change']), reverse=True)
        return [m['symbol'] for m in sorted_list[:15]]
    except Exception as e:
        print(f"⚠️ 리스트 생성 에러: {e}")
        return []

# check_v80_signal, execute_v80_trade 함수는 기존 통합본과 동일하게 유지

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🚀 V80 [진짜 15% 필터] 엔진 재가동")
    print("------------------------------------------")
    
    while True:
        try:
            balance = exchange.fetch_balance()
            total_balance = balance.get('total', {}).get('USDT', 0)
            
            # 15% 필터 적용 리스트
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            
            # 자산별 슬롯
            max_slots = 1 if total_balance < 3000 else 2

            print(f"\n[잔고: {total_balance:.1f}$] 변동성 15% 이상 종목 {len(watch_list)}개 발견")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                # 현재 등락률도 같이 표기하도록 로그 강화 ㅡㅡ;ㅋ
                ticker = exchange.fetch_ticker(symbol)
                cur_pct = ticker.get('percentage', 0)
                print(f"[{time.strftime('%H:%M:%S')}] 🔥 {symbol:15} ({cur_pct}%): {signal}")
                
                if signal in ["LONG", "SHORT"]:
                    execute_v80_trade(exchange, symbol, signal, max_slots)
                time.sleep(0.3)
            
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ 시스템 루프 에러: {e}")
            time.sleep(5)
