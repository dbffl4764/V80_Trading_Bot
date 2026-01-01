# 1. 모든 찌꺼기 프로세스 강제 종료
sudo pkill -9 -f python3

# 2. main.py 파일을 순수한 파이썬 코드로 강제 재생성 (오염된 깃허브 무시)
cat << 'EOF' > main.py
import ccxt, time, os, pandas as pd
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
        self.target_roe = 100.0
        self.half_profit_taken = False
        self.highest_price = 0

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}", flush=True)

    def check_v80_signal(self, symbol):
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            m5 = df['c'].rolling(5).mean().iloc[-1]
            m20 = df['c'].rolling(20).mean().iloc[-1]
            m60 = df['c'].rolling(60).mean().iloc[-1]
            curr = df['c'].iloc[-1]
            ma_gap = abs(m20 - m60) / m60 * 100
            
            # 사령관님 원본 V80 로직
            if 3.5 <= ma_gap <= 15.0:
                if m5 > m20 > m60 and curr > m5: return "LONG", curr
                if m60 > m20 > m5 and curr < m5: return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            self.ex.set_leverage(self.leverage, symbol)
            bal = float(self.ex.fetch_balance()['total']['USDT'])
            
            # 자산별 종목수 지침 반영
            if bal < 3000: max_pos = 1
            elif bal < 5000: max_pos = 2
            elif bal < 10000: max_pos = 3
            else: max_pos = 5
            
            # 40% 자산 사용, 20배 레버리지
            amount = float(self.ex.amount_to_precision(symbol, (bal * 0.4 / max_pos * self.leverage) / entry_price))
            
            # 1. 진입
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"⚔️ {symbol} {side} 진입완료")

            # 2. 서버 손절 예약 (ROE -35%)
            sl_p = entry_price * (1 - 0.0175) if side == "LONG" else entry_price * (1 + 0.0175)
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                 amount, None, {'stopPrice': self.ex.price_to_precision(symbol, sl_p), 'reduceOnly': True})
            
            self.half_profit_taken = False
            self.highest_price = entry_price

            while True:
                time.sleep(3)
                ticker = self.ex.fetch_ticker(symbol); curr = ticker['last']
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                curr_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                if curr_amt == 0: break
                
                roe = ((curr - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * self.leverage)
                if side == "LONG": self.highest_price = max(self.highest_price, curr)
                else: self.highest_price = min(self.highest_price, curr)

                # [익절 로직] 100% 수익 시 50% 익절 후 방어선 수익권으로 이동
                if not self.half_profit_taken and roe >= 100.0:
                    self.ex.cancel_all_orders(symbol)
                    half_qty = float(self.ex.amount_to_precision(symbol, curr_amt / 2))
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', half_qty, {'reduceOnly': True})
                    
                    # 나머지 절반은 ROE 50% 지점에 서버 예약
                    safe_p = entry_price * 1.025 if side == "LONG" else entry_price * 0.975
                    self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                         half_qty, None, {'stopPrice': self.ex.price_to_precision(symbol, safe_p), 'reduceOnly': True})
                    self.half_profit_taken = True
                    self.log(f"💰 1차 익절 완료! 방어선 ROE 50% 지점 배치.")

                # [추격 로직] 반익절 후 고점 대비 1% 하락 시 전량 익절
                if self.half_profit_taken:
                    drop = (self.highest_price - curr) / self.highest_price * 100 if side == "LONG" else (curr - self.highest_price) / self.highest_price * 100
                    if drop >= 1.0:
                        self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', curr_amt, {'reduceOnly': True})
                        self.log(f"🏁 고점 대비 1% 하락! 최종 익절 완료. ROE: {roe:.2f}%")
                        break
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log("🛡️ V80 Iron-Clad 실전 가동 (20배 레버리지)")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                targets = sorted([s for s, t in tickers.items() if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 10.0], 
                                key=lambda x: tickers[x].get('quoteVolume', 0), reverse=True)[:15]
                for s in targets:
                    side, price = self.check_v80_signal(s)
                    if side: self.execute_mission(s, side, price); break
                time.sleep(20)
            except Exception as e: print(e); time.sleep(10)

if __name__ == "__main__":
    V80_Final_Striker().run()
EOF

# 3. 백그라운드 실행 및 실시간 로그 확인
nohup python3 -u main.py > binance.out 2>&1 &
tail -f binance.out
