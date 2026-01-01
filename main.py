import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Final_Survivor:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 20
        self.max_entry_count = 3 

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}")

    def run(self):
        self.log("🚀 3분할 사격 엔진 기동 (에러 수정 완료)")
        while True:
            try:
                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 5: break

                ts = self.ex.fetch_tickers()
                targets = []
                for s, t in ts.items():
                    # [수정] t['percentage']가 None인 경우를 대비한 안전 로직
                    percent = t.get('percentage')
                    if s.endswith('/USDT:USDT') and percent is not None:
                        if abs(percent) >= 10.0:
                            targets.append(s)
                
                targets = sorted(targets, key=lambda x: ts[x].get('quoteVolume', 0), reverse=True)[:15]

                for s in targets:
                    o = self.ex.fetch_ohlcv(s, '5m', limit=65)
                    df = pd.DataFrame(o, columns=['t','o','h','l','c','v'])
                    c = df['c']
                    m5, m20, m60 = c.rolling(5).mean().iloc[-1], c.rolling(20).mean().iloc[-1], c.rolling(60).mean().iloc[-1]
                    curr, gap = c.iloc[-1], abs(m20 - m60) / m60 * 100

                    if 3.5 <= gap <= 15.0:
                        side = 'buy' if m5 > m20 > m60 and curr > m5 else ('sell' if m60 > m20 > m5 and curr < m5 else None)
                        
                        if side:
                            self.ex.set_leverage(self.leverage, s)
                            firepower = (bal * 0.9) / self.max_entry_count
                            entry_price = curr
                            
                            for i in range(1, self.max_entry_count + 1):
                                amt = float(self.ex.amount_to_precision(s, (firepower * self.leverage) / curr))
                                self.ex.create_market_order(s, side, amt)
                                self.log(f"🎯 [{s}] {i}차 분할 진입 완료!")
                                
                                if i == 1:
                                    sl_p = curr * (1-0.0175) if side == 'buy' else curr * (1+0.0175)
                                    self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == 'buy' else 'buy', 
                                                         amt * self.max_entry_count, None, {'stopPrice': self.ex.price_to_precision(s, sl_p), 'reduceOnly': True})
                                time.sleep(1)

                            high_p, half_taken = curr, False
                            while True:
                                time.sleep(3)
                                ticker = self.ex.fetch_ticker(s); now_p = ticker['last']
                                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == s]
                                curr_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                                if curr_amt == 0: break

                                roe = ((now_p - entry_price) / entry_price * 100 * self.leverage) if side == 'buy' else ((entry_price - now_p) / entry_price * 100 * self.leverage)
                                high_p = max(high_p, now_p) if side == 'buy' else min(high_p, now_p)

                                if not half_taken and roe >= 100.0:
                                    self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', curr_amt / 2, {'reduceOnly': True})
                                    half_taken = True
                                    self.log(f"💰 [반익절] 100% 달성!")

                                if half_taken:
                                    drop = (high_p - now_p) / high_p * 100 if side == 'buy' else (now_p - high_p) / high_p * 100
                                    if drop >= 1.0:
                                        self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', abs(float(pos[0]['positionAmt'])), {'reduceOnly': True})
                                        self.log(f"🏁 [최종 익절] 고점대비 1% 하락. ROE: {roe:.2f}%")
                                        break
                            break
                time.sleep(15)
            except Exception as e:
                print(f"에러 무시 및 재가동: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_Final_Survivor().run()
