import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Ironclad:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 20
        self.loss_count = 0 
        self.safety_limit = 2000.0

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}", flush=True)

    def run(self):
        self.log("🚀 [오류 수정 완료] 47불 부활 작전 재가동")
        while True:
            try:
                if self.loss_count >= 3:
                    self.log("❌ 3연패 달성! 지침에 따라 셧다운."); break

                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 10: break

                ts = self.ex.fetch_tickers()
                targets = []
                for s, t in ts.items():
                    # [에러 수정] percentage가 None일 경우 0.0으로 처리
                    pct = t.get('percentage') if t.get('percentage') is not None else 0.0
                    if s.endswith('/USDT:USDT') and 'BTC' not in s and abs(pct) >= 10.0:
                        targets.append(s)
                
                targets = sorted(targets, key=lambda x: ts[x].get('quoteVolume', 0), reverse=True)[:10]

                for s in targets:
                    o = self.ex.fetch_ohlcv(s, '5m', limit=100)
                    df = pd.DataFrame(o, columns=['t','o','h','l','c','v'])
                    c = df['c']
                    m5, m20, m60 = c.rolling(5).mean().iloc[-1], c.rolling(20).mean().iloc[-1], c.rolling(60).mean().iloc[-1]
                    
                    # 60-20 이격도 (1~7%) 및 정렬 확인
                    gap_60_20 = abs(m60 - m20) / m60 * 100
                    curr = c.iloc[-1]
                    
                    side = None
                    # 정배열 + 이격수렴 + 5일선 위 (롱)
                    if (m5 > m20 > m60) and (1.0 <= gap_60_20 <= 7.0) and (curr > m5):
                        # [추세선 로직] 전고점 돌파 확인
                        if curr > df['h'].iloc[-2]: side = 'buy'
                    # 역배열 + 이격수렴 + 5일선 아래 (숏)
                    elif (m60 > m20 > m5) and (1.0 <= gap_60_20 <= 7.0) and (curr < m5):
                        # [추세선 로직] 전저점 이탈 확인
                        if curr < df['l'].iloc[-2]: side = 'sell'

                    if side:
                        self.ex.set_leverage(self.leverage, s)
                        # 2000불 미만 2분할, 47불 기준 한 발당 약 21불 사격
                        max_entry = 2 if bal < self.safety_limit else 3
                        qty = float(self.ex.amount_to_precision(s, (bal * 0.95 * self.leverage / max_entry) / curr))
                        
                        # 최소 주문금액(5불 이상) 체크
                        if qty * curr / self.leverage < 5: continue

                        sl_p = float(self.ex.price_to_precision(s, curr * (1 - 0.0175) if side == 'buy' else curr * (1 + 0.0175)))

                        # 1차 진입 & 즉시 스탑로스
                        self.ex.create_market_order(s, side, qty)
                        self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == 'buy' else 'buy', qty * max_entry, None, {'stopPrice': sl_p, 'reduceOnly': True})
                        self.log(f"🎯 {s} {side} 사격! (이격: {gap_60_20:.2f}%, 손절: {sl_p})")

                        # 2차 사격 (수익 구간 시)
                        time.sleep(10)
                        now_p = self.ex.fetch_ticker(s)['last']
                        if (side == 'buy' and now_p > curr) or (side == 'sell' and now_p < curr):
                            self.ex.create_market_order(s, side, qty)
                            self.log("📦 2차 후속탄 완료.")

                        # 익절 관리 (100% 반익절 / 1% 트레일링)
                        high_p, half_taken = now_p, False
                        while True:
                            time.sleep(10)
                            pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == s]
                            c_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                            if c_amt == 0: 
                                self.ex.cancel_all_orders(s)
                                if not half_taken: self.loss_count += 1
                                break
                            
                            p_now = self.ex.fetch_ticker(s)['last']
                            roe = ((p_now - curr) / curr * 100 * self.leverage) if side == 'buy' else ((curr - p_now) / curr * 100 * self.leverage)
                            high_p = max(high_p, p_now) if side == 'buy' else min(high_p, p_now)

                            if not half_taken and roe >= 100:
                                self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', c_amt / 2, {'reduceOnly': True})
                                half_taken = True; self.loss_count = 0
                                self.log("💰 100% 반익절 성공!")

                            if half_taken:
                                drop = (high_p - p_now) / high_p * 100 if side == 'buy' else (p_now - high_p) / high_p * 100
                                if drop >= 1.0:
                                    self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', c_amt, {'reduceOnly': True})
                                    break
                        break
                time.sleep(20)
            except Exception as e:
                self.log(f"⚠️ 시스템 오류 보정 중: {e}"); time.sleep(10)

if __name__ == "__main__":
    V80_Ironclad().run()
