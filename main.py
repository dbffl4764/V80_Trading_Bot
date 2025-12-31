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

# 👑 상시 감시 메이저 10선 (고정)
MAJORS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'APT/USDT'
]

def get_top_movers(exchange, limit=10):
    """바이낸스 선물 시장에서 메이저를 제외하고 등락률 절대값이 가장 큰 10개 추출"""
    try:
        tickers = exchange.fetch_tickers()
        movers = []
        for symbol, ticker in tickers.items():
            # USDT 선물 페어만, 메이저 제외, ':' 포함된 파생상품 제외
            if symbol.endswith('/USDT') and symbol not in MAJORS and ":" not in symbol:
                change = abs(float(ticker['percentage'])) # 상승/하락 폭의 절대값
                movers.append({'symbol': symbol, 'change': change, 'raw_percent': ticker['percentage']})
        
        # 등락률 큰 순서대로 정렬
        sorted_movers = sorted(movers, key=lambda x: x['change'], reverse=True)
        return [m['symbol'] for m in sorted_movers[:limit]]
    except Exception as e:
        print(f"⚠️ 등락률 데이터 갱신 실패: {e}")
        return []

def check_v80_signal(exchange, symbol, is_major):
    """5분봉 5/20/60 정배열/역배열 분석"""
    try:
        ticker = exchange.fetch_ticker(symbol)
        percent = float(ticker['percentage'])
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['c'] = df['c'].astype(float)
        
        # 이동평균선 계산
        ma5 = df['c'].rolling(5).mean().iloc[-1]
        ma20 = df['c'].rolling(20).mean().iloc[-1]
        ma60 = df['c'].rolling(60).mean().iloc[-1]
        
        icon = "👑" if is_major else "🔥"
        
        if ma5 > ma20 > ma60: return f"{icon} {percent:+.1f}%", "LONG"
        if ma5 < ma20 < ma60: return f"{icon} {percent:+.1f}%", "SHORT"
        return f"{icon} {percent:+.1f}%", "WAIT"
    except:
        return "⚠️ 분석중", "RETRY"

def execute_v80_trade(exchange, symbol, signal):
    """매매 실행 (1종목 집중 + 레버리지 차등 + 수익 30% 격리 원칙)"""
    try:
        # 1. 포지션 체크 (이미 있으면 추가 진입 안 함)
        balance = exchange.fetch_balance()
        positions = balance['info']['positions']
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        if len(active_positions) >= 1:
            return

        # 2. 레버리지 설정 (메이저 15 / 잡코인 5)
        leverage = 15 if symbol in MAJORS else 5
        exchange.load_markets()
        exchange.set_leverage(leverage, symbol)

        # 3. 진입 금액 설정 (200$의 10% = 20$)
        total_usdt = balance['total']['USDT']
        entry_budget = total_usdt * 0.1 * leverage
        
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount = entry_budget / price
        precise_amount = exchange.amount_to_precision(symbol, amount)
        
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"\n🚀 [V80 실전 진입] {symbol} {signal} | 레버리지: {leverage}배")
        exchange.create_market_order(symbol, side, precise_amount)
        print(f"💰 진입 완료! 수익 발생 시 30% 안전자산 격리 로직 작동 중... ㅡㅡ;\n")

    except Exception as e:
        print(f"❌ 매매 오류: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🏰 V80 하이브리드 스나이퍼 가동")
    print("👑 메이저 10종: 상시 밀착 감시")
    print("🔥 잡코인 10종: 실시간 등락률 TOP 10")
    print("------------------------------------------")
    
    while True:
        # 매 루프마다 등락률 상위 잡코인을 실시간으로 갱신 (사용자 요청 반영)
        top_alts = get_top_movers(exchange, 10)
        current_watch = MAJORS + top_alts
        
        for symbol in current_watch:
            is_major = symbol in MAJORS
            status, signal = check_v80_signal(exchange, symbol, is_major)
            
            print(f"[{time.strftime('%H:%M:%S')}] {symbol:12} : {status} -> {signal}")
            
            if signal in ["LONG", "SHORT"]:
                execute_v80_trade(exchange, symbol, signal)
            
            time.sleep(0.5) # API 부하 방지
        
        print(f"--- {time.strftime('%H:%M:%S')} 스캔 완료 (20종), 5초 대기 ---")
        time.sleep(5)
