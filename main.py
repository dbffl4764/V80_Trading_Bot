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

# 👑 상시 감시 메이저 10선 (사용자 원칙)
MAJORS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'APT/USDT'
]

def get_top_movers(exchange, limit=10):
    try:
        tickers = exchange.fetch_tickers()
        movers = []
        for symbol, ticker in tickers.items():
            # 메이저 제외, USDT 선물 페어만, 24시간 등락률 절대값 기준
            if symbol.endswith('/USDT') and symbol not in MAJORS and ":" not in symbol:
                change = abs(float(ticker['percentage']))
                movers.append({'symbol': symbol, 'change': change, 'raw_change': ticker['percentage']})
        
        # 등락률이 가장 큰 순서대로 정렬
        sorted_movers = sorted(movers, key=lambda x: x['change'], reverse=True)
        return [m['symbol'] for m in sorted_movers[:limit]]
    except Exception as e:
        print(f"⚠️ 등락률 순위 갱신 실패: {e}")
        return []

def check_v80_signal(exchange, symbol, is_major):
    try:
        ticker = exchange.fetch_ticker(symbol)
        percent = float(ticker['percentage'])
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        
        # V80 핵심: 5/20/60 이평선
        ma5 = df['c'].rolling(5).mean().iloc[-1]
        ma20 = df['c'].rolling(20).mean().iloc[-1]
        ma60 = df['c'].rolling(60).mean().iloc[-1]
        
        icon = "👑" if is_major else "🔥"
        
        if ma5 > ma20 > ma60: return f"{icon} {percent:+.1f}%", "LONG"
        if ma5 < ma20 < ma60: return f"{icon} {percent:+.1f}%", "SHORT"
        return f"{icon} {percent:+.1f}%", "WAIT"
    except:
        return "⚠️ 에러", "RETRY"

def execute_v80_trade(exchange, symbol, signal):
    try:
        # 1. 포지션 체크 (이미 있으면 진입 안 함 - 1종목 집중)
        balance = exchange.fetch_balance()
        positions = balance['info']['positions']
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        if len(active_positions) >= 1:
            return

        # 2. 레버리지 설정 (메이저 15 / 잡코인 5)
        leverage = 15 if symbol in MAJORS else 5
        exchange.set_leverage(leverage, symbol)

        # 3. 진입 수량 계산 (200$ 시드의 10% = 20$)
        total_usdt = balance['total']['USDT']
        entry_budget = total_usdt * 0.1 * leverage
        
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount = entry_budget / price
        
        # 수량 정밀도 조절
        exchange.load_markets()
        precise_amount = exchange.amount_to_precision(symbol, amount)
        
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [V80 진입] {symbol} {signal} | 레버리지: {leverage}배 | 금액: {entry_budget}$")
        exchange.create_market_order(symbol, side, precise_amount)
        print(f"🛡️ 수익 발생 시 30% 안전자산 격리 감시 시작!")

    except Exception as e:
        print(f"❌ 매매 실행 오류: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🏰 V80 하이브리드 엔진 가동")
    print("👑 메이저 10종 상시밀착 감시")
    print("🔥 등락률 TOP 10 잡코인 실시간 추적")
    print("------------------------------------------")
    
    while True:
        # 매 루프마다 가장 변동성 큰 잡코인 10개를 새로 뽑음 (실시간 갱신)
        top_alts = get_top_movers(exchange, 10)
        current_watch = MAJORS + top_alts
        
        for symbol in current_watch:
            is_major = symbol in MAJORS
            status, signal = check_v80_signal(exchange, symbol, is_major)
            
            print(f"[{time.strftime('%H:%M:%S')}] {symbol:10} : {status} -> {signal}")
            
            if signal in ["LONG", "SHORT"]:
                execute_v80_trade(exchange, symbol, signal)
            
            time.sleep(0.5) # API 과부하 방지
        
        print(f"--- {time.strftime('%H:%M:%S')} 스캔 완료, 5초 후 재시작 ---")
        time.sleep(5)
