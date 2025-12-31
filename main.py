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

# 👑 메이저 명단 (기억은 하되, 3000불 미만이면 무시함!)
MAJORS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'APT/USDT'
]

def get_dynamic_watchlist(exchange, total_balance):
    """3000불 미만이면 메이저 무시, 잡코인 10개만 추출"""
    try:
        tickers = exchange.fetch_tickers()
        candidates = []
        
        for symbol, t in tickers.items():
            if symbol.endswith('/USDT') and ":" not in symbol:
                # 메이저는 등락률 순위 계산에서 일단 제외
                if symbol not in MAJORS:
                    change = abs(float(t['percentage']))
                    candidates.append({'symbol': symbol, 'change': change})

        # 등락률 큰 순서대로 잡코인 10개 선정
        sorted_alts = sorted(candidates, key=lambda x: x['change'], reverse=True)
        top_alts = [m['symbol'] for m in sorted_alts[:10]]

        # [사용자 원칙 핵심] 3000불 이상일 때만 메이저 합류! 그 전엔 무시! ㅡㅡ;
        if total_balance >= 3000:
            return MAJORS + top_alts
        
        return top_alts # 3000불 미만이면 오직 🔥잡코인 10개만 리턴
    except Exception as e:
        print(f"⚠️ 데이터 갱신 에러: {e}")
        return []

def check_v80_signal(exchange, symbol):
    """V80 5분봉 정배열 분석"""
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

# 매매 실행 함수 (사용자 자산별 슬롯 원칙 적용)
def execute_v80_trade(exchange, symbol, signal, max_slots):
    try:
        balance = exchange.fetch_balance()
        positions = [p for p in balance['info']['positions'] if float(p['positionAmt']) != 0]
        if len(positions) >= max_slots: return

        price = float(exchange.fetch_ticker(symbol)['last'])
        leverage = 15 if price >= 5000 else 5 # 5000불 넘는 것만 15배
        exchange.set_leverage(leverage, symbol)

        entry_budget = (balance['total']['USDT'] * 0.1) * leverage
        amount = exchange.amount_to_precision(symbol, entry_budget / price)
        
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [V80 진입] {symbol} {signal} ({leverage}배)")
        exchange.create_market_order(symbol, side, amount)
    except Exception as e: print(f"❌ 매매 오류: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🏰 V80 스마트 사령부 엔진 (3000$ 미만 메이저 무시)")
    print("------------------------------------------")
    
    while True:
        try:
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            
            # 자산 기반 슬롯 및 감시 리스트 결정
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            if total_balance < 3000: max_slots = 1
            elif total_balance < 5000: max_slots = 2
            else: max_slots = 3

            print(f"\n[잔고: {total_balance:.1f}$] {len(watch_list)}개 종목 추적 중...")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                icon = "👑" if symbol in MAJORS else "🔥"
                print(f"[{time.strftime('%H:%M:%S')}] {icon} {symbol:12} : {signal}")
                
                if signal in ["LONG", "SHORT"]:
                    execute_v80_trade(exchange, symbol, signal, max_slots)
                time.sleep(0.5)
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ 루프 에러: {e}")
            time.sleep(5)
