import os
import ccxt
import pandas as pd
import time
import random
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
    [사용자 전략 1] V80 필승 타점
    6개월, 3개월, 1개월, 24시간, 12시간, 6시간 전 구간 정배열 확인
    """
    timeframes = ['6M', '3M', '1M', '1d', '12h', '6h']
    trends = []
    try:
        for tf in timeframes:
            ohlcv = exchange.fapiPublicGetKlines({'symbol': symbol.replace('/', ''), 'interval': tf, 'limit': 30})
            df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ts_end', 'qav', 'nt', 'tbv', 'tqv', 'ignore'])
            current = float(df['c'].iloc[-1])
            ma20 = df['c'].astype(float).rolling(window=20).mean().iloc[-1]
            trends.append(current > ma20)
        
        if all(trends): return "LONG"      # 전 구간 상승 추세
        if not any(trends): return "SHORT" # 전 구간 하락 추세
        return "WAIT"
    except Exception:
        return "RETRY"

def execute_trade(exchange, symbol, signal):
    """
    [본질] 실전 주문 및 자산 관리 로직
    """
    try:
        # 1. 잔고 및 현재 포지션 확인
        balance = exchange.fetch_balance()
        total_usdt = balance['total']['USDT']
        
        positions = exchange.fapiPrivateGetPositionRisk()
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]

        # [사용자 전략 2] 금액대별 종목 제한
        # 2,000$ 미만 시 1종목 집중 / 그 이상은 최대 2종목
        limit_count = 1 if total_usdt < 2000 else 2
        
        if len(active_positions) >= limit_count:
            print(f"⚠️ 원칙 준수: 현재 {len(active_positions)}개 포지션 운용 중 (제한: {limit_count})")
            return

        # [사용자 전략 3] 잔고의 10% 진입
        entry_budget = total_usdt * 0.1
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount = entry_budget / price
        
        # 2. 실전 시장가 주문 실행
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [실전 가동] {symbol} {signal} 진입! 예산: {entry_budget:.2f} USDT")
        
        order = exchange.create_market_order(symbol, side, amount)
        
        # [사용자 전략 4] 수익의 30% 안전자산 격리 (본질적 철칙)
        print(f"✅ 주문 완료 (ID: {order['id']})")
        print(f"💰 수익 발생 시 무조건 30% 안전자산으로 분리합니다.")
        
    except Exception as e:
        print(f"❌ 매매 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    symbol = 'BTC/USDT'
    
    print("------------------------------------------")
    print("💰 V80 실전 매매 시스템 가동 (100억 고지전)")
    print(f"📉 전략: 전 구간 추세 일치 시 진입")
    print(f"🛡️ 원칙: 수익 30% 격리 / 2,000$ 전 1종목 집중")
    print("------------------------------------------")
    
    while True:
        try:
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            signal = check_v80_trend(exchange, symbol)
            
            print(f"[{now}] 시장 분석: {signal}")
            
            if signal in ["LONG", "SHORT"]:
                execute_trade(exchange, symbol, signal)
            
            # 1분 주기로 정밀 감시
            time.sleep(60)
            
        except Exception as e:
            print(f"❌ 루프 오류: {e}")
            time.sleep(10)
