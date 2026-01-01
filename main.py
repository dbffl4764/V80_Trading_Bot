import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Infinite_Striker:
    def __init__(self):
        # 바이낸스 선물 계정 설정
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 10
        self.total_profit_pct = 0 # 누적 수익 관리용

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏰 {msg}", flush=True)

    def get_active_symbol(self):
        """현재 활성화된 포지션 확인"""
        try:
            balance = self.ex.fetch_balance()
            positions = balance['info']['positions']
            for p in positions:
                if float(p['positionAmt']) != 0:
                    return p['symbol'].replace('USDT', '/USDT:USDT'), float(p['positionAmt'])
            return None, 0
        except: return None, 0

    def check_v80_signal(self, symbol):
        """[서열 확인] 5>20>60 정배열 롱 / 5<20<60 역배열 숏 판독"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            ma5 = df['c'].rolling(5).mean().iloc[-1]
            ma20 = df['c'].rolling(20).mean().iloc[-1]
            ma60 = df['c'].rolling(60).mean().iloc[-1]
            curr = df['c'].iloc[-1]
            
            # 서열 체크 (사령관님 강조 사항)
            is_perfect_long = (ma5 > ma20) and (ma20 > ma60)
            is_perfect_short = (ma5 < ma20) and (ma20 < ma60)
            
            gap = abs(curr - ma20) / ma20 * 100

            if gap <= 2.5:
                if is_perfect_long and curr > ma20:
                    self.log(f"💎 [서열통과] {symbol} 정배열 롱 타점 (5>20>60)")
                    return "LONG", curr
                elif is_perfect_short and curr < ma20:
                    self.log(f"💀 [서열통과] {symbol} 역배열 숏 타점 (5<20<60)")
                    return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        """1차분 손절 시스템 예약 및 수익 시 불타기 시퀀스"""
        try:
            # 1. 시드 40%의 1/3 화력 계산
            bal = self.ex.fetch_balance()['free'].get('USDT', 0)
            firepower = (bal * 0.4) / 3 
            first_amount = (firepower * self.leverage) / entry_price
            
            # 2. 1차 포격 (시장가)
            self.log(f"🎯 [진격] {symbol} {side} 사격! (화력: {firepower:.2f}USDT)")
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', first_amount)
            
            # 3. [방패] 바이낸스 서버에 즉시 스탑로스(-35%) 예약
            stop_price = entry_price * 0.965 if side == "LONG" else entry_price * 1.035
            params = {
                'stopPrice': self.ex.price_to_precision(symbol, stop_price), 
                'reduceOnly': True
            }
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', first_amount, None, params)
            self.log(f"🛡️ [시스템 방어] -35% 지점에 스탑로스 예약 완료")

            step = 1
            while True:
                ticker = self.ex.fetch_ticker(symbol)
                curr_price = ticker['last']
                
                # ROE 계산 (레버리지 10배 기준)
                roe = ((curr_price - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr_price) / entry_price * 100 * self.leverage)

                # [손절 발생 시 루프 탈출]
                if roe <= -35.0:
                    self.log(f"🚨 [손절] 1차분 도려내기 완료. 다음 타겟 정찰.")
                    break 

                # [불타기 시퀀스]
                if step == 1 and roe >= 150.0:
                    self.log(f"🔥 [불타기] 150% 돌파! 2차 화력 투입!")
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', first_amount)
                    step = 2

                if step == 2 and roe >= 300.0:
                    self.log(f"🚀 [불타기] 300% 돌파! 극한 수익 진입!")
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', first_amount)
                    step = 3

                # 포지션 종료 여부 확인
                s, amt = self.get_active_symbol()
                if not s:
                    self.log("🏁 상황 종료. 정찰 모드로 복귀합니다.")
                    break
                time.sleep(10)

        except Exception as e:
            self.log(f"⚠️ 작전 중 오류: {e}")

    def run(self):
        self.log(f"⚔️ V80 최종 스트라이커 발진! (잔고: {self.ex.fetch_balance()['total'].get('USDT', 0):.2f})")
        while True:
            try:
                symbol, amt = self.get_active_symbol()
                if amt == 0:
                    self.log("👀 타겟 탐색 중... (5% 변동 종목 정찰)")
                    tickers = self.ex.fetch_tickers()
                    candidates = []
                    for s, t in tickers.items():
                        if s.endswith('/USDT:USDT'):
                            change = t.get('percentage') if t.get('percentage') is not None else 0.0
                            if abs(change) >= 5.0:
                                candidates.append({'s': s, 'v': t.get('quoteVolume', 0)})
                    
                    for cand in sorted(candidates, key=lambda x: x['v'], reverse=True)[:10]:
                        side, price = self.check_v80_signal(cand['s'])
                        if side:
                            self.execute_mission(cand['s'], side, price)
                            break
                time.sleep(15)
            except Exception as e:
                self.log(f"⚠️ 메인 루프 에러: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_Infinite_Striker().run()
