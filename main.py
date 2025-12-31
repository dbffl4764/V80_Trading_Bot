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

# 👑 메이저 코인 명단 (3000불 이상일 때만 활성화됨)
MAJORS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'APT/USDT'
]

def get_dynamic_watchlist(exchange, total_balance):
    """자산이 3000불 미만이면 메이저를 무시하고 잡코인 10개만 추출"""
    try:
        tickers = exchange.fetch_tickers()
        alts_candidates = []
        
        for symbol, t in tickers.items():
            if symbol.endswith('/USDT') and ":" not in symbol:
                # 메이저는 등락률 순위(TOP 10)에서 제외하고 따로 관리
                if symbol not in MAJORS:
                    change = abs(float(t['percentage']))
                    alts_candidates.append({'symbol': symbol, 'change': change})

        # 등락률 큰 순서대로 잡코인 10개 선정
        sorted_alts = sorted(alts_candidates, key=lambda x: x['change'], reverse=True)
        top_alts = [m['symbol'] for m in sorted_alts[:10]]

        # [핵심] 자산이 3000불 이상일 때만 메이저를 감시 리스트에 포함 (그 전엔 무시)
        if total_balance >= 3000:
            return MAJORS + top_alts
        
        return top_alts # 3000불 미만이면 오직 🔥잡코인 10개만!
    except Exception as e:
        print(f"⚠️ 리스트 갱신 에러: {e}")
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

# ... (execute_v80_trade 함수 등 생략)

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🏰 V80 스마트 자산 관리 시스템 가동")
    print("💰 3000불 미만: 메이저 코인 '무시' 모드")
    print("------------------------------------------")
    
    while True:
        try:
            # 1. 실시간 잔고 확인
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            
            # 2. 잔고에 따른 유동적 감시 리스트 생성
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            
            # 3. 자산별 동시 진입 슬롯 설정 (사용자 원칙)
            if total_balance < 3000: max_slots = 1
            elif total_balance < 5000: max_slots = 2
            elif total_balance < 10000: max_slots = 3
            else: max_slots = 5

            print(f"\n[자산: {total_balance:.1f}$] {len(watch_list)}개 종목 추적 중 (최대 {max_slots}종목)")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                icon = "👑" if symbol in MAJORS else "🔥"
                print(f"[{time.strftime('%H:%M:%S')}] {icon} {symbol:12} : {signal}")
                
                # 매매 로직 (생략 - 슬롯 제한 및 수익 30% 격리 포함)
                # if signal in ["LONG", "SHORT"]: execute_v80_trade(...)
                
                time.sleep(0.5)
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ 루프 에러: {e}")
            time.sleep(5)
