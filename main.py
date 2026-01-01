import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_IronClad_Striker:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 20
        self.stop_loss_percent = 0.0175 # 20배 기준 ROE -35% (가격 -1.75%)
        self.half_profit_roe = 100.0
        self.trail_percent = 0.01 # 고점 대비 1% (ROE -20%p)
        self.highest_price = 0

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}", flush=True)

    def execute_mission(self, symbol, side, entry_price):
        try:
            # 1. 포지션 진입 및 레버리지 설정
            self.ex.set_leverage(self.leverage, symbol)
            total_bal = float(self.ex.fetch_balance()['total']['USDT'])
            
            # 자산별 종목 수 (사령관님 지침 반영)
            if total_bal < 3000: max_pos = 1
            elif total_bal < 5000: max_pos = 2
            elif total_bal < 10000: max_pos = 3
            else: max_pos = 5

            qty = (total_bal * 0.4 / max_pos * self.leverage) / entry_price
            amount = float(self.ex.amount_to_precision(symbol, qty))
            
            # 진입 (시장가)
            order = self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"⚔️ 진입완료: {symbol} {side} {amount}개")

            # 2. 거래소 서버에 즉시 손절 주문 (ROE -35% 지점)
            sl_price = entry_price * (1 - self.stop_loss_percent) if side == "LONG" else entry_price * (1 + self.stop_loss_percent)
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                 amount, None, {'stopPrice': self.ex.price_to_precision(symbol, sl_price), 'reduceOnly': True})
            
            self.half_profit_taken = False
            self.highest_price = entry_price

            while True:
                time.sleep(2) # 감시 속도 최대로 (2초)
                ticker = self.ex.fetch_ticker(symbol)
                curr = ticker['last']
                
                # 포지션 확인
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                curr_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                if curr_amt == 0: break # 포지션 종료 시 루프 탈출
                
                roe = ((curr - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * self.leverage)
                
                # 고점 갱신
                if side == "LONG": self.highest_price = max(self.highest_price, curr)
                else: self.highest_price = min(self.highest_price, curr) if self.highest_price != 0 else curr

                # 3. 1차 익절 (ROE 100% 도달)
                if not self.half_profit_taken and roe >= self.half_profit_roe:
                    # 기존 스탑로스 취소
                    self.ex.cancel_all_orders(symbol)
                    # 50% 시장가 익절
                    half_qty = float(self.ex.amount_to_precision(symbol, curr_amt / 2))
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', half_qty, {'reduceOnly': True})
                    
                    # 남은 50%에 대해 '수익 방어선(ROE +50%)' 스탑로스 서버 예약
                    safe_price = entry_price * (1 + 0.025) if side == "LONG" else entry_price * (1 - 0.025)
                    self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                         half_qty, None, {'stopPrice': self.ex.price_to_precision(symbol, safe_price), 'reduceOnly': True})
                    
                    self.half_profit_taken = True
                    self.log(f"💰 1차익절 완료! 나머지 물량 ROE +50%에 철벽 방어선 구축.")

                # 4. Trailing Stop (고점 대비 1% 하락 시)
                if self.half_profit_taken:
                    drop = (self.highest_price - curr) / self.highest_price * 100 if side == "LONG" else (curr - self.highest_price) / self.highest_price * 100
                    if drop >= 1.0:
                        self.ex.cancel_all_orders(symbol)
                        self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', curr_amt, {'reduceOnly': True})
                        self.log(f"🏁 고점 대비 1% 하락! 똑바로 전량 익절했습니다. (ROE: {roe:.2f}%)")
                        # 수익 30% 안전자산 알림
                        self.log("📢 [명령] 수익의 30%를 즉시 현물 계좌로 이체하십시오!")
                        break
        except Exception as e: self.log(f"⚠️ 에러 발생: {e}")
