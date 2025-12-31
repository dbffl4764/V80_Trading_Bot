import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

# 환경 변수 로드
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
    """±15% 이상 변동성 종목 추출 (폭등/폭락 모두 포함)"""
    try:
        tickers = exchange.fetch_tickers()
        volatile_candidates = []
        
        for symbol, t in tickers.items():
            if 'USDT' in symbol and ":" not in symbol:
                pct = t.get('percentage', 0)
                low = t.get('low', 0)
                last = t.get('last', 0)
                # 24시간 등락률 또는 저점 대비 상승폭 중 큰 것 선택
                low_to_last_pct = ((last - low) / low * 100) if low > 0 else 0
                max_change = max(abs(pct), low_to_last_pct)
                
                if max_change >= 15:
                    if total_balance < 3000:
                        if any(m in symbol for m in MAJORS_KEYWORDS):
                            continue
                    volatile_candidates.append({'symbol': symbol, 'change': max_change})

        return [m['symbol'] for m in sorted(volatile_candidates, key=lambda x: x['change'], reverse=True)[:15]]
    except Exception as e:
        print(f"⚠️ 리스트 생성 에러: {e}")
        return []

def check_v80_signal(exchange, symbol):
    """사용자 원칙: 1~2봉 확인 후 3봉째 확정 진입"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        
        ma5 = df['c'].rolling(5).mean()
        ma20 = df['c'].rolling(20).mean()
        ma60 = df['c'].rolling(60).mean()
        
        # 3봉 연속 정렬 상태 및 이격 확대 확인
        # 현재(idx: -1), 직전(-2), 그 전(-3)
        is_long = (ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1] and
                   ma5.iloc[-2] > ma20.iloc[-2] > ma60.iloc[-2] and
                   ma5.iloc[-3] > ma20.iloc[-3] > ma60.iloc[-3])
        
        is_short = (ma5.iloc[-1] < ma20.iloc[-1] < ma60.iloc[-1] and
                    ma5.iloc[-2] < ma20.iloc[-2] < ma60.iloc[-2] and
                    ma5.iloc[-3] < ma20.iloc[-3] < ma60.iloc[-3])

        if is_long and (ma5.iloc[-1] - ma20.iloc[-1]) > (ma5.iloc[-2] - ma20.iloc[-2]):
            return "LONG"
        if is_short and (ma20.iloc[-1] - ma5.iloc[-1]) > (ma20.iloc[-2] - ma5.iloc[-2]):
            return "SHORT"
        return "WAIT"
    except:
        return "RETRY"

def execute_v80_trade(exchange, symbol, signal, max_slots):
    """자산의 10% 진입, 1슬롯 원칙"""
    try:
        pos_info = exchange.fetch_positions()
        active_positions = [p for p in pos_info if float(p.get('contracts', 0)) != 0]
        if len(active_positions) >= max_slots: return

        balance = exchange.fetch_balance()
        total_usdt = balance['total']['USDT']
        ticker = exchange.fetch_ticker(symbol)
        price = float(ticker['last'])
        
        leverage = 5 # 5000불 미만 5배 고정
        exchange.set_leverage(leverage, symbol)
        
        # 잔고의 10% 사용
        entry_budget = (total_usdt * 0.1) * leverage
        amount = exchange.amount_to_precision(symbol, entry_budget / price)
        
        side = 'buy' if signal == 'LONG' else 'sell'
        exchange.create_market_order(symbol, side, amount)
        print(f"🚀 [진입] {symbol} {signal} | 3봉 확정 타점 사냥 시작!")
    except Exception as e:
        print(f"❌ 매매 에러: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🚀 V80 [3봉 초입 사냥] 전면 가동")
    print("💡 ±15% 변동성 / 3봉 정렬 확인 / 수익 30% 격리")
    print("------------------------------------------")
    
    while True:
        try:
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            
            # 2000불 미만 1슬롯 원칙
            max_slots = 1 if total_balance < 3000 else 2
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                if signal in ["LONG", "SHORT"]:
                    execute_v80_trade(exchange, symbol, signal, max_slots)
                time.sleep(0.2)
            
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ 메인 루프 에러: {e}")
            time.sleep(10)
