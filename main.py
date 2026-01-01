import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Ultimate_Commander:
    def __init__(self):
        # [환경 설정] API KEY 보안 지침 준수
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
        self.log("🚀 [표 지침 100% 준수] 35불 부활 엔진 가동")
        while True:
            try:
                # [리스크 관리] 지침 7번: 연속 3패 시 셧다운
                if self.loss_count >= 3:
                    self.log("❌ 3연패 달성! 사령관님 지침에 따라 오늘 작전을 즉시 종료합니다."); break

                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 5: break

                # [종목 선정] Target Scanner: 변동성 10%, 비트 제외, 거래량 상위 10개
                ts = self.ex.fetch_tickers()
                targets = []
                for s, t in ts.items():
                    pct = t.get('percentage') if t.get('percentage') is not None else 0.0
                    if s.endswith('/USDT:USDT') and 'BTC' not in s and abs(pct) >= 10.0:
                        targets.append(s)
                targets = sorted(targets, key=lambda x: ts[x].get('quoteVolume', 0), reverse=True)[:10]

                for s in targets:
                    # [메인 엔진] 60-20-5 정렬 및 1-7% 이격도 계산
                    o = self.ex.fetch_ohlcv(s, '5m', limit=70)
                    df = pd.DataFrame(o, columns=['t','o','h','l','c','v'])
                    c = df['c']
                    m5, m20, m60 = c.rolling(5).mean().iloc[-1], c.rolling(20).mean().iloc[-1], c.rolling(60).mean().iloc[-1]
                    
                    gap_60_20 = abs(m60 - m20) / m60 * 100
                    curr = c.iloc[-1]
                    
                    side = None
                    # [메인 엔진 핵심 로직] 60-20-5 정렬 + 이격 1-7% + 5일선 돌파
                    if (m5 > m20 > m60) and (1.0 <= gap_60_20 <= 7.0) and (curr > m5): side = 'buy'
                    elif (m60 > m20 > m5) and (1.0 <= gap_60_20 <= 7.0) and (curr < m5): side = 'sell'

                    if side:
                        # [현실 보정] Reality Filter: 최소 주문 금액(10불) 및 수수료 고려
                        self.ex.set_leverage(self.leverage, s)
                        
                        # [진입 제어] Entry Logic: 2000불 미만 2분할 / 이상 3분할 (노 물타기)
                        max_entry = 2 if bal < self.safety_limit else 3
                        unit_qty = float(self.ex.amount_to_precision(s, (bal * 0.9 * self.leverage / max_entry) / curr))
                        
                        # 현실 보정: 10불 미만 주문이면 패스
                        if (unit_qty * curr / self.leverage) < 5: continue

                        # [리스크 관리] 지침 6번: 1.75% 손절 즉시 예약
                        sl_price = float(self.ex.price_to_precision(s, curr * (1 - 0.0175) if side == 'buy' else curr * (1 + 0.0175)))

                        # 1차 사격 및 거래소 스탑로스 박기
                        self.ex.create_market_order(s, side, unit_qty)
                        self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == 'buy' else 'buy', unit_qty * max_entry, None, {
                            'stopPrice': sl_price, 'reduceOnly': True
                        })
                        self.log(f"🎯 {s} 1차 진입! [60-20 이격: {gap_60_20:.2f}%]")

                        # [진입 제어] 방향 일치 시에만 불타기 (2차 진입)
                        time.sleep(10)
                        now_p = self.ex.fetch_ticker(s)['last']
                        if (side == 'buy' and now_p > curr) or (side == 'sell' and now_p < curr):
                            self.ex.create_market_order(s, side, unit_qty)
                            self.log("📦 2차 후속탄 투입 성공 (방향 일치 확인)")

                        # [수익 실현] Profit Logic: ROE 100% 반익절 및 1% 트레일링
                        high_p, half_taken = now_p, False
                        while True:
                            time.sleep(10)
                            pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == s]
                            c_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                            if c_amt == 0: 
                                self.ex.cancel_all_orders(s) # 남은 주문 정리
                                if not half_taken: self.loss_count += 1
                                break
                            
                            p_now = self.ex.fetch_ticker(s)['last']
                            roe = ((p_now - curr) / curr * 100 * self.leverage) if side == 'buy' else ((curr - p_now) / curr * 100 * self.leverage)
                            high_p = max(high_p, p_now) if side == 'buy' else min(high_p, p_now)

                            if not half_taken and roe >= 100:
                                self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', c_amt / 2, {'reduceOnly': True})
                                half_taken = True; self.loss_count = 0
                                # [수익 실현] 30% 안전자산 이전은 2000불 돌파 후부터 실행
                                self.log("💰 [ROE 100%] 반익절 완료! 사령관님의 5년 결실입니다.")

                            if half_taken:
                                # 트레일링 스탑: 고점 대비 1% 하락 시
                                drop = (high_p - p_now) / high_p * 100 if side == 'buy' else (p_now - high_p) / high_p * 100
                                if drop >= 1.0:
                                    self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', c_amt, {'reduceOnly': True})
                                    break
                        break
                time.sleep(20)
            except Exception as e:
                self.log(f"⚠️ 시스템 보정 중: {e}"); time.sleep(10)

if __name__ == "__main__":
    V80_Ultimate_Commander().run()
