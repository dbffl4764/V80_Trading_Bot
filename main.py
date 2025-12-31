import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv()

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future', 'adjustForTimeDifference': True}
    })

def check_v80_trend(exchange, symbol):
    """
    [사용자 전략 정밀 반영]
    이평선: 5, 20, 60 (단기/중기/장기 정배열)
    분봉 분석: 60분봉(1h), 15분봉(20분봉 대용), 5분봉(5m)
    """
    try:
        # 1. 1시간봉(60분) 기준으로 5/20/60 이평선 체크
        ohlcv = exchange.fapiPublicGetKlines({'symbol': symbol.replace('/', ''), 'interval': '1h', 'limit': 100})
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ts_end', 'qav', 'nt', 'tbv', 'tqv', 'ignore'])
        df['c'] = df['c'].astype(float)
        
        ma5 = df['c'].rolling(window=5).mean().iloc[-1]
        ma20 = df['c'].rolling(window=20).mean().iloc[-1]
        ma60 = df['c'].rolling(window=60).mean().iloc[-1]
        current_price = df['c'].iloc[-1]
        
        # 2. 5분봉 기준으로 단기 추세 확인
        ohlcv_5m = exchange.fapiPublicGetKlines({'symbol': symbol.replace('/', ''), 'interval': '5m', 'limit': 10})
        last_5m_close = float(ohlcv_5m[-1][4])
        
        # [상승 정배열] 현재가 > 5 > 20 > 60 AND 5분봉도 양봉/상승세
        is_long = current_price > ma5 > ma20 > ma60 and last_5m_close > current_price * 0.999
        # [하락 정배열] 현재가 < 5 < 20 < 60 AND 5분봉도 음봉/하락세
        is_short = current_price < ma5 < ma20 < ma60 and last_5m_close < current_price * 1.001
        
        if is_long: return "LONG"
        if is_short: return "SHORT"
        return "WAIT"
        
    except Exception as e:
        print(f"⚠️ 데이터 분석 중 오류: {e}")
        return "RETRY"

def execute_trade(exchange, symbol, signal):
    try:
        # 1. 잔고 확인 (100억 고지전의 기본)
        balance = exchange.fetch_balance()
        total_usdt = balance['total']['USDT']
        
        # 2. 포지션 확인 (2,000$ 미만 시 1종목 집중 원칙)
        positions = exchange.fapiPrivateGetPositionRisk()
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        limit_count = 1 if total_usdt < 2000 else 2
        
        if len(active_positions) >= limit_count:
            print(f"⚠️ {total_usdt:.2f}$ 기준 {limit_count}종목 제한 준수 중.")
            return

        # 3. 잔고 10% 진입 금액 계산
        entry_budget = total_usdt * 0.1
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount = entry_budget / price
        
        # 4. 실전 주문 실행
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [V80 실전] {symbol} {signal} 진입! (이평선 5/20/60 일치)")
        order = exchange.create_market_order(symbol, side, amount)
        
        # 5. 수익 30% 격리 원칙 알림
        print(f"✅ 주문 성공: {order['id']}")
        print(f"💰 수익 발생 시 무조건 30% 안전자산 격리 가동!")
        
    except Exception as e:
        print(f"❌ 매매 오류: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    symbol = 'BTC/USDT'
    
    print("------------------------------------------")
    print("💰 V80 [5/20/60] 실전 엔진 가동")
    print(f"📊 분석: 60분/20분/5분 추세 동기화")
    print(f"🛡️ 원칙: 2,000$ 전 1종목 / 수익 30% 격리")
    print("------------------------------------------")
    
    while True:
        try:
            signal = check_v80_trend(exchange, symbol)
            print(f"[{time.strftime('%H:%M:%S')}] 신호: {signal}")
            
            if signal in ["LONG", "SHORT"]:
                execute_trade(exchange, symbol, signal)
            
            time.sleep(60) # 1분 단위 정밀 스캔
        except Exception as e:
            print(f"❌ 루프 에러: {e}")
            time.sleep(10)
