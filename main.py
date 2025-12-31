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

def get_trading_strategy(total_balance):
    """사용자 자산 규모별 운영 원칙 적용"""
    if total_balance < 3000:
        # 3000불 미만: 잡코인 집중, 최대 1종목 (2000불까지 1개 원칙 포함)
        return {'max_slots': 1, 'watch_majors': False}
    elif total_balance < 5000:
        # 3000불 이상: 메이저 포함, 최대 2종목
        return {'max_slots': 2, 'watch_majors': True}
    elif total_balance < 10000:
        # 5000불 이상: 최대 3종목
        return {'max_slots': 3, 'watch_majors': True}
    else:
        # 1만불 이상: 최대 5종목
        return {'max_slots': 5, 'watch_majors': True}

def get_realtime_watchlist(exchange, watch_majors):
    """등락률 상위 10개 잡코인 + 5000불 이상 메이저 필터링"""
    try:
        tickers = exchange.fetch_tickers()
        alts = []
        majors_5k = []
        
        for symbol, t in tickers.items():
            if not symbol.endswith('/USDT') or ":" in symbol: continue
            
            price = float(t['last'])
            change = abs(float(t['percentage']))
            
            if price >= 5000:
                majors_5k.append(symbol)
            else:
                alts.append({'symbol': symbol, 'change': change})

        # 등락률 큰 순서대로 10개 추출
        sorted_alts = sorted(alts, key=lambda x: x['change'], reverse=True)
        top_alts = [m['symbol'] for m in sorted_alts[:10]]

        if watch_majors:
            return majors_5k + top_alts
        return top_alts
    except Exception as e:
        print(f"⚠️ 리스트 갱신 실패: {e}")
        return []

def check_v80_signal(exchange, symbol):
    """V80 핵심: 5분봉 5/20/60 정배열 분석"""
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
    """자산별 슬롯 제한을 준수하는 매매 실행"""
    try:
        # 1. 현재 포지션 수 확인
        balance = exchange.fetch_balance()
        positions = balance['info']['positions']
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        if len(active_positions) >= max_slots:
            return # 슬롯 꽉 차면 패스

        # 2. 레버리지 설정 (비트/이더 15배, 나머지 5배)
        price = float(exchange.fetch_ticker(symbol)['last'])
        leverage = 15 if price >= 5000 else 5
        exchange.set_leverage(leverage, symbol)

        # 3. 진입 수량 (자산의 10% 사용)
        total_usdt = balance['total']['USDT']
        entry_budget = (total_usdt * 0.1) * leverage
        amount = entry_budget / price
        
        exchange.load_markets()
        precise_amount = exchange.amount_to_precision(symbol, amount)
        
        side = 'buy' if signal == 'LONG' else 'sell'
        print(f"🚀 [V80 진입] {symbol} {signal} | 슬롯({len(active_positions)+1}/{max_slots})")
        exchange.create_market_order(symbol, side, precise_amount)
        print(f"🛡️ 수익 발생 시 30% 안전자산 격리 원칙 사수! ㅡㅡ;")

    except Exception as e:
        print(f"❌ 매매 오류: {e}")

if __name__ == "__main__":
    exchange = get_exchange()
    print("------------------------------------------")
    print("🏰 V80 자산별 전략 사령부 가동")
    print("------------------------------------------")
    
    while True:
        try:
            # 1. 내 자산 확인 및 전략 결정
            balance = exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            strategy = get_trading_strategy(total_balance)
            
            # 2. 실시간 감시 종목 갱신
            watch_list = get_realtime_watchlist(exchange, strategy['watch_majors'])
            
            print(f"\n[잔고: {total_balance:.1f}$] {len(watch_list)}개 종목 스캔 중 (최대 {strategy['max_slots']}종목)")
            
            for symbol in watch_list:
                signal = check_v80_signal(exchange, symbol)
                
                # 로그 출력 (검색은 계속함 ㅡㅡ;)
                print(f"[{time.strftime('%H:%M:%S')}] {symbol:12} : {signal}")
                
                if signal in ["LONG", "SHORT"]:
                    execute_v80_trade(exchange, symbol, signal, strategy['max_slots'])
                
                time.sleep(0.5)
            
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ 루프 에러: {e}")
            time.sleep(10)
