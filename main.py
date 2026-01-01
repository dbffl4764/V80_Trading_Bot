import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Final_Striker:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 20
        self.stop_loss_roe = -35.0  # 초기 손절 라인
        self.half_profit_roe = 100.0  # 1차 익절 라인
        self.trail_percent = 1.0    # 고점 대비 1% 하락 시 전량 익절
        
        self.half_profit_taken = False
        self.highest_price = 0

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}", flush=True)

    def execute_mission(self, symbol, side, entry_price):
        try:
            self.ex.set_leverage(self.leverage, symbol)
            bal = float(self.ex.fetch_balance()['total']['USDT'])
            
            # 사령관님 자금 관리 원칙 반영
            if bal < 3000: max_pos = 1
            elif bal < 5000: max_pos = 2
            elif bal < 10000: max_pos = 3
            else: max_pos = 5

            # 진입 수량 계산 (자산의 40% 사용 / 분할 사격 3회 가정 없이 즉시 투입)
            qty = (bal * 0.4 / max_pos * self.leverage) / entry_price
            amount = float(self.ex.amount_to_precision(symbol, qty))

            # 1. 포지션 진입
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"⚔️ {symbol} {side} 진입 완료! (수량: {amount})")

            # 2. 초기 손절 서버 예약 (ROE -35%)
            sl_price = entry_price * (1 - 0.0175) if side == "LONG" else entry_price * (1 + 0.0175)
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                 amount, None, {'stopPrice': self.ex.price_to_precision(symbol, sl_price), 'reduceOnly': True})
            
            self.half_profit_taken = False
            self.highest_price = entry_price

            while True:
                time.sleep(2) # 20배 레버리지 대응용 2초 초정밀 감시
                ticker = self.ex.fetch_ticker(symbol)
                curr = ticker['last']
                
                # 포지션 확인
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                curr_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                if curr_amt == 0: break 
                
                roe = ((curr - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * self.leverage)
                
                # 고점 갱신
                if side == "LONG": self.highest_price = max(self.highest_price, curr)
                else: self.highest_price = min(self.highest_price, curr) if self.highest_price != 0 else curr

                # 3. 1차 익절 및 스탑로스 수익권 이동 (똑바로 로직)
                if not self.half_profit_taken and roe >= self.half_profit_roe:
                    # 기존 모든 주문 취소 (기존 손절 주문 제거)
                    self.ex.cancel_all_orders(symbol)
                    
                    # 50% 시장가 익절
                    half_qty = float(self.ex.amount_to_precision(symbol, curr_amt / 2))
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', half_qty, {'reduceOnly': True})
                    
                    # 나머지 50% 물량에 대해 'ROE +50% 지점'에 철벽 스탑로스 예약
                    # 가격 기준 2.5% 변동 지점 = ROE 50%
                    safe_price = entry_price * 1.025 if side == "LONG" else entry_price * 0.975
                    self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                         half_qty, None, {'stopPrice': self.ex.price_to_precision(symbol, safe_price), 'reduceOnly': True})
                    
                    self.half_profit_taken = True
                    self.log(f"💰 [1차 익절] 50% 확보 완료! 남은 물량 'ROE +50% 지점'으로 방어선 전진 배치.")

                # 4. Trailing Stop (고점 대비 가격 1% 하락 시)
                if self.half_profit_taken:
                    drop = (self.highest_price - curr) / self.highest_price * 100 if side == "LONG" else (curr - self.highest_price) / self.highest_price * 100
                    
                    if drop >= self.trail_percent:
                        self.ex.cancel_all_orders(symbol) # 예약된 방어선 주문 취소
                        self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', curr_amt, {'reduceOnly': True})
                        self.log(f"🏁 [최종 익절] 고점 대비 1% 하락! 수익 똑바로 챙겼습니다. 최종 ROE: {roe:.2f}%")
                        break
                        
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    # ... (생략된 run 및 신호 체크 로직은 기존과 동일) ...
