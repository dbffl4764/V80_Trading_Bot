import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

# API 키 로드
load_dotenv(dotenv_path='/home/dbffl4764/V80_Trading_Bot/.env')

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

# 👑 봇의 기억 속에 있는 메이저 (3000불 미만이면 무시 대상)
MAJORS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'APT/USDT'
]

def get_dynamic_watchlist(exchange, total_balance):
    """자산 상태에 따라 사냥감을 결정 (3000불 미만은 잡코인 10개만)"""
    try:
        tickers = exchange.fetch_tickers()
        candidates = []
        
        for symbol, t in tickers.items():
            # USDT 선물 페어 + 파생상품 제외 + 메이저 제외 (3000불 미만일 때)
            if symbol.endswith('/USDT') and ":" not in symbol:
                if total_balance < 3000:
                    if symbol not in MAJORS:
                        change = abs(float(t['percentage']))
                        candidates.append({'symbol': symbol, 'change': change})
                else:
                    # 3000불 이상이면 메이저 포함해서 전부 후보군
                    change = abs(float(t['percentage']))
                    candidates.append({'symbol': symbol, 'change': change})

        # 등락률 큰 순서대로 정렬
        sorted_list = sorted(candidates, key=lambda x: x['change'], reverse=True)
        top_10_alts = [m['symbol'] for m in sorted_list[:10]]

        # 자산 3000불 이상일 때만 메이저 고정 추가
        if total_balance >= 3000:
            # 중복 제거 및 리스트 합치기
            final_list = list(dict.fromkeys(MAJORS + top_10_alts))
            return final_list
            
        return top_10_alts # 3000불 미만이면 닥치고 잡코인 10개!
    except Exception as e:
        print(f"⚠️ 리스트 갱신 에러: {e}")
        return []

def check_v80_signal(exchange, symbol):
    """V80 5분봉 5/20/60 정배열 분석"""
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

def execute_v80_trade(exchange, symbol, signal, max_slots):
    """자산별 슬롯 원칙 준수 매매"""
    try:
        balance = exchange.fetch_balance()
        # 현재 실제 포지션 수 확인
        pos_info = exchange.fetch_positions()
        active_positions = [p for p in pos_info if float(p['contracts']) != 0]
        
        if len(active_positions) >= max_slots: return

        ticker = exchange.fetch_ticker(symbol)
        price = float(ticker['last'])
        
        # 레버리지: 시가 5000불 이상 메이저 15배, 나머지 5배
        leverage = 15 if price >= 5000 else 5
        exchange.set_leverage(leverage, symbol)

        # 수량 계산 (자산의 10% 사용)
        entry_budget = (balance['total']['USDT'] * 0.1) * leverage
        amount = exchange.amount_to_precision(symbol, entry_budget / price)
        
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [V80 진입] {symbol} {signal} | 자산 대비 {leverage}배")
        exchange.create_market_order(symbol, side, amount)
    except Exception as e:
        print(f"❌ 매매 실행 에러: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🏰 V80 잡코인 사냥 엔진 가동 (3000$ 미만 메이저 무시)")
    print("------------------------------------------")
    
    while True:
        try:
            # 1. 자산 확인 및 전략 설정
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            
            # 자산에 따른 감시 리스트 (3000불 미만은 잡코인만)
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            
            # 자산 규모별 최대 진입 슬롯
            if total_balance < 3000: max_slots = 1
            elif total_balance < 5000: max_slots = 2
            else: max_slots = 3

            print(f"\n[잔고: {total_balance:.1f}$] {len(watch_list)}개 종목 추적 중 (최대 {max_slots}슬롯)")
            
            if not watch_list:
                print("👀 조건에 맞는 종목이 없습니다. 다시 찾는 중...")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                icon = "👑" if symbol in MAJORS else "🔥"
                print(f"[{time.strftime('%H:%M:%S')}] {icon} {symbol:12} : {signal}")
                
                if signal in ["LONG", "SHORT"]:
                    execute_v80_trade(exchange, symbol, signal, max_slots)
                time.sleep(0.5)
            
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ 시스템 루프 에러: {e}")
            time.sleep(10)
