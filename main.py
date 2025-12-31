import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

# API 키 및 환경변수 로드
load_dotenv(dotenv_path='/home/dbffl4764/V80_Trading_Bot/.env')

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

# 👑 봇의 기억 속에 있는 메이저 명단 (무시는 하지만 삭제는 안 함!)
MAJORS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'APT/USDT'
]

def get_dynamic_watchlist(exchange, total_balance):
    """사용자 자산 상태에 따라 사냥감을 결정하는 로직"""
    try:
        tickers = exchange.fetch_tickers()
        candidates = []
        
        # 1. 모든 종목을 훑으면서 메이저가 아닌 놈들 중 등락률 후보군 수집
        for symbol, t in tickers.items():
            if symbol.endswith('/USDT') and ":" not in symbol:
                if symbol not in MAJORS:
                    change = abs(float(t['percentage']))
                    candidates.append({'symbol': symbol, 'change': change})

        # 2. 등락률(절대값)이 가장 큰 잡코인 10개 추출
        sorted_alts = sorted(candidates, key=lambda x: x['change'], reverse=True)
        top_10_alts = [m['symbol'] for m in sorted_alts[:10]]

        # [핵심] 자산이 3,000불 미만이면 메이저를 '무시'하고 잡코인만 리턴!
        if total_balance < 3000:
            return top_10_alts
        
        # 자산이 3,000불 이상이면? 그제서야 메이저 10개를 감시 리스트에 포함!
        return MAJORS + top_10_alts
        
    except Exception as e:
        print(f"⚠️ 데이터 갱신 실패: {e}")
        return []

def check_v80_signal(exchange, symbol):
    """V80 5분봉 5/20/60 정배열 분석"""
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

# ... (execute_v80_trade 함수 등 기존 매매 로직 포함)

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🚀 V80 성장형 사령부 가동 (3000$ 미만 메이저 무시)")
    print("------------------------------------------")
    
    while True:
        try:
            # 1. 현재 내 자산 확인
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            
            # 2. 자산에 따른 유동적 타겟 선정
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            
            # 3. 자산 규모별 최대 진입 슬롯 설정 (2000불 1개, 3000불 2개 등)
            if total_balance < 3000: max_slots = 1
            elif total_balance < 5000: max_slots = 2
            elif total_balance < 10000: max_slots = 3
            else: max_slots = 5

            print(f"\n[잔고: {total_balance:.1f}$] {len(watch_list)}개 종목 추적 중 (최대 {max_slots}슬롯)")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                icon = "👑" if symbol in MAJORS else "🔥"
                print(f"[{time.strftime('%H:%M:%S')}] {icon} {symbol:12} : {signal}")
                
                # 매매 로직 (슬롯 여유 있을 때만 진입)
                # if signal in ["LONG", "SHORT"]: execute_v80_trade(...)
                
                time.sleep(0.5)
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ 에러 발생: {e}")
            time.sleep(5)
