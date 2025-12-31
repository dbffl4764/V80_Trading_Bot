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
    try:
        tickers = exchange.fetch_tickers()
        volatile_candidates = []
        
        for symbol, t in tickers.items():
            if '/USDT' in symbol and ":" not in symbol:
                if t.get('percentage') is None: continue
                
                change_percent = float(t['percentage'])
                
                # 💡 사용자 원칙: ±15% 이상 변동성 코인만!
                if abs(change_percent) >= 15:
                    # 자산 3000불 미만 시 메이저 무시
                    if total_balance < 3000:
                        if any(m in symbol for m in MAJORS_KEYWORDS):
                            continue
                    
                    volatile_candidates.append({'symbol': symbol, 'change': change_percent})

        sorted_list = sorted(volatile_candidates, key=lambda x: abs(x['change']), reverse=True)
        return [m['symbol'] for m in sorted_list[:15]]
    except Exception as e:
        print(f"⚠️ 리스트 생성 에러: {e}")
        return []

def check_v80_signal(exchange, symbol):
    """V80 핵심: 5분봉 5/20/60 이동평균선 정배열 분석"""
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
    """자산별 슬롯 제한 준수 매매 실행"""
    try:
        balance = exchange.fetch_balance()
        pos_info = exchange.fetch_positions()
        active_positions = [p for p in pos_info if float(p.get('contracts', 0)) != 0]
        
        if len(active_positions) >= max_slots: return

        ticker = exchange.fetch_ticker(symbol)
        price = float(ticker['last'])
        
        # 레버리지: 5000불 이상 15배, 나머지 5배
        leverage = 15 if price >= 5000 else 5
        exchange.set_leverage(leverage, symbol)

        # 자산의 10% 진입
        total_usdt = balance.get('total', {}).get('USDT', 0)
        entry_budget = (total_usdt * 0.1) * leverage
        amount = exchange.amount_to_precision(symbol, entry_budget / price)
        
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [진입] {symbol} {signal} | 레버리지 {leverage}배")
        exchange.create_market_order(symbol, side, amount)
    except Exception as e:
        print(f"❌ 매매 에러: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🏰 V80 스나이퍼 엔진 통합 완료 (±15% 필터)")
    print("------------------------------------------")
    
    while True:
        try:
            balance = exchange.fetch_balance()
            total_balance = balance.get('total', {}).get('USDT', 0)
            
            watch_list = get_dynamic_watchlist(exchange, total_balance)
            
            # 자산별 슬롯 원칙
            if total_balance < 3000: max_slots = 1
            elif total_balance < 5000: max_slots = 2
            else: max_slots = 3

            print(f"\n[잔고: {total_balance:.1f}$] 15%이상 종목 {len(watch_list)}개 발견 (슬롯: {max_slots})")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                print(f"[{time.strftime('%H:%M:%S')}] 🔥 {symbol:15} : {signal}")
                
                if signal in ["LONG", "SHORT"]:
                    execute_v80_trade(exchange, symbol, signal, max_slots)
                time.sleep(0.5)
            
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ 시스템 루프 에러: {e}")
            time.sleep(10)
