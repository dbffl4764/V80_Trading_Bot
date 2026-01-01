import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Real_Split_Striker:
    def __init__(self):
        self.ex = ccxt.binance({'apiKey': os.getenv('BINANCE_API_KEY'), 'secret': os.getenv('BINANCE_SECRET_KEY'), 'options': {'defaultType': 'future'}, 'enableRateLimit': True})
        self.leverage = 20

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}")

    def run(self):
        self.log("🚀 진짜 3분할 평단 방어 엔진 가동")
        while True:
            try:
                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 10: break

                ts = self.ex.fetch_tickers()
                targets = [s for s, t in ts.items() if s.endswith('/USDT:USDT') and t.get('percentage') is not None and abs(t['percentage']) >= 10.0]
                targets = sorted(targets, key=lambda x: ts[x].get('quoteVolume', 0), reverse=True)[:10]

                for s in targets:
                    o = self.ex.fetch_ohlcv(s, '5m', limit=65)
                    df = pd.DataFrame(o, columns=['t','o','h','l','c','v'])
                    c = df['c']
                    m5, m20, m60 = c.rolling(5).mean().iloc[-1], c.rolling(20).mean().iloc[-1], c.rolling(60).mean().iloc[-1]
                    curr = c.iloc[-1]
                    gap = abs(m20 - m60) / m60 * 100

                    if 3.5 <= gap <= 15.0:
                        side = 'buy' if m5 > m20 > m60 and curr > m5 else ('sell' if m60 > m20 > m5 and curr < m5 else None)
                        
                        if side:
                            self.ex.set_leverage(self.leverage, s)
                            # [3분할 전략] 1차(20%), 2차(30%), 3차(50%) 비중 조절
                            portions = [0.2, 0.3, 0.5]
                            total_amt = 0
                            self.log(f"🎯 {s} {side.upper()} 3분할 작전 시작")

                            for i, pct in enumerate(portions):
                                now_p = self.ex.fetch_ticker(s)['last']
                                # 130불의 해당 비중만큼 사격
                                firepower = bal * 0.9 * pct
                                amt = float(self.ex.amount_to_precision(s, (firepower * self.leverage) / now_p))
                                self.ex.create_market_order(s, side, amt)
                                total_amt += amt
                                self.log(f"📦 {i+1}차 진입 완료 ({int(pct*100)}% 비중)")
                                
                                if i == 0: # 1차 진입 후 손절 예약
                                    sl_p = now_p * (1-0.0175) if side == 'buy' else now_p * (1+0.0175)
                                    self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == 'buy' else 'buy', 
                                                         amt * 5, None, {'stopPrice': self.ex.price_to_precision(s, sl_p), 'reduceOnly': True})
                                
                                if i < 2: time.sleep(10) # 다음 분할 사격까지 10초 대기 (평단 분산)

                            # 익절 관리 (100% 반익절 + 1% 트레일링)
                            high_p, half_taken = now_p, False
                            entry_avg = now_p # 대략적인 평단
                            while True:
                                time.sleep(3)
                                now_p = self.ex.fetch_ticker(s)['last']
                                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == s]
                                c_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                                if c_amt == 0: break

                                roe = ((now_p - entry_avg) / entry_avg * 100 * self.leverage) if side == 'buy' else ((entry_avg - now_p) / entry_avg * 100 * self.leverage)
                                high_p = max(high_p, now_p) if side == 'buy' else min(high_p, now_p)

                                if not half_taken and roe >= 100.0:
                                    self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', c_amt / 2, {'reduceOnly': True})
                                    half_taken = True
                                    self.log("💰 100% 반익절 성공!")

                                if half_taken:
                                    drop = (high_p - now_p) / high_p * 100 if side == 'buy' else (now_p - high_p) / high_p * 100
                                    if drop >= 1.0:
                                        self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', c_amt, {'reduceOnly': True})
                                        self.log(f"🏁 1% 하락 전량 익절. ROE: {roe:.2f}%")
                                        break
                            break
                time.sleep(15)
            except Exception as e:
                print(f"에러: {e}"); time.sleep(10)

if __name__ == "__main__":
    V80_Real_Split_Striker().run()
