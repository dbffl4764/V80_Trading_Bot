import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

# 환경 변수 로드 (API KEY 등)
load_dotenv(dotenv_path='/home/dbffl4764/V80_Trading_Bot/.env')

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

def get_trading_strategy(total_balance):
    """자산 구간별 운영 원칙 (3000불 미만은 오직 잡코인 10개만 공략)"""
    if total_balance < 3000:
        return {'max_slots': 1, 'search_majors': False}
    elif total_balance < 5000:
        return {'max_slots': 2, 'search_majors': True}
    elif total_balance < 10000:
        return {'max_slots': 3, 'search_majors': True}
    else:
        return {'max_slots': 5, 'search_majors': True}

def get_realtime_watchlist(exchange, search_majors):
    """자산이 3000불 안 되면 메이저는 검색조차 안 하고 등락률 TOP 10만 추출"""
    try:
        tickers = exchange.fetch_tickers()
        candidates = []
        majors_5k = []
        
        for symbol, t in tickers.items():
            if not symbol.endswith('/USDT') or ":" in symbol: continue
            
            price = float(t['last'])
            change = abs(float(t['percentage']))
            
            if price >= 5000:
                majors_5k.append(symbol)
            else:
                candidates.append({'symbol': symbol, 'change': change, 'raw_percent': t['percentage']})

        # [핵심] 등락률(절대값)이 가장 큰 놈들 10개만 추출
        sorted_alts = sorted(candidates, key=lambda x: x['change'], reverse=True)
        top_10_alts = [m['symbol'] for m in sorted_alts[:10]]

        # 자산 3000불 미만이면 majors_5k는 버리고 오직 top_10_alts만 반환 ㅡㅡ;
        if search_majors:
            return majors_5k + top_10_alts
        return top_10_alts
    except Exception as e:
        print(f"⚠️ 리스트 갱신 에러: {e}")
        return []

def check_v80_signal(exchange, symbol):
    """5분봉 5/20/60 정배열/역배열 분석"""
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
    except:
        return "RETRY"

def execute_v80_trade(exchange, symbol, signal, max_slots):
    """자산별 진입 슬롯 제한 준수 매매"""
    try:
        balance = exchange.fetch_balance()
        positions = balance['info']['positions']
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        # 슬롯 꽉 찼으면 더 안 삼 ㅡㅡ;
        if len(active_positions) >= max_slots:
            return

        # 레버리지: 시가 5000불 이상 15배, 나머지 5배
        price = float(exchange.fetch_ticker(symbol)['last'])
        leverage = 15 if price >= 5000 else 5
        exchange.set_leverage(leverage, symbol)

        # 수량 계산 (자산의 10% 사용)
        total_usdt = balance['total']['USDT']
        entry_budget = (total_usdt * 0.1) * leverage
        amount = entry_budget / price
        
        exchange.load_markets()
        precise_amount = exchange.amount_to_precision(symbol, amount)
        
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [진입 성공] {symbol} {signal} | 슬롯: {len(active_positions)+1}/{max_slots}")
        exchange.create_market_order(symbol, side, precise_amount)
        print(f"💰 수익의 30%는 무조건 안전자산으로 빼는 거 잊지 마세요! ㅋ")

    except Exception as e:
        print(f"❌ 매매 실행 실패: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🔥 V80 [잡코인 10선] 스나이퍼 모드 가동")
    print("💰 3000불 미만: 메이저 검색 전면 차단")
    print("------------------------------------------")
    
    while True:
        try:
            # 1. 현재 잔고 확인 및 전략(슬롯 수) 결정
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            strategy = get_trading_strategy(total_balance)
            
            # 2. 감시 리스트 (자산에 따라 잡코인만 혹은 메이저 포함)
            watch_list = get_realtime_watchlist(exchange, strategy['search_majors'])
            
            print(f"\n[현재 자산: {total_balance:.1f}$] {len(watch_list)}개 종목 추적 중...")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                
                # 로그 출력
                print(f"[{time.strftime('%H:%M:%S')}] 🔥 {symbol:12} : {signal}")
                
                # 타점 포착 시 매매 실행
                if signal in ["LONG", "SHORT"]:
                    execute_v80_trade(exchange, symbol, signal, strategy['max_slots'])
                
                time.sleep(0.5) # API 부하 방지
            
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ 에러 발생: {e}")
            time.sleep(10)
