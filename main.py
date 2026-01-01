import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# GCP 환경에서 API KEY 보안을 위해 .env 로드
load_dotenv()

class CommanderStrategyV80:
    def __init__(self):
        # 바이낸스 선물 거래소 연결
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 20
        self.loss_count = 0  # 연속 패배 카운트용 (3회 패배 시 중단)
        self.safety_threshold = 2000.0  # 2,000불 전까지는 무조건 재투자

    def log(self, msg):
        # GCP 서버 터미널 실시간 확인을 위해 flush=True 필수
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🛡️ {msg}", flush=True)

    def run(self):
        self.log("🚀 [40불 최후 작전] 구글 서버 엔진 가동 (목표: 2,000불)")
        while True:
            try:
                # [지침 1] 연속 3번 패하면 그날은 중단
                if self.loss_count >= 3:
                    self.log("❌ 연속 3회 패배 발생! 사령관님 지침에 따라 금일 작전을 종료합니다.")
                    break

                # 잔고 확인
                bal_info = self.ex.fetch_balance()
                bal = float(bal_info['total']['USDT'])
                if bal < 5: 
                    self.log("총알 부족으로 가동 중단.")
                    break
                
                # [지침 2] 2,000불 미만일 때는 안전자산 이체 없음 (전액 재투자)
                if bal < self.safety_threshold:
                    self.log(f"📊 현재 잔고 {bal:.2f} USDT. (공격적 복리 운용 모드)")

                # [지침 3] 10% 변동성 알트만 타겟 (비트코인 제외)
                ts = self.ex.fetch_tickers()
                targets = []
                for s, t in ts.items():
                    pct = t.get('percentage')
                    if s.endswith('/USDT:USDT') and pct is not None:
                        if abs(pct) >= 10.0 and 'BTC' not in s:
                            targets.append(s)
                
                # 거래량 상위 10개 종목 추출
                targets = sorted(targets, key=lambda x: ts[x].get('quoteVolume', 0), reverse=True)[:10]

                for s in targets:
                    # 5분봉 데이터 65개 (60선 계산용)
                    o = self.ex.fetch_ohlcv(s, '5m', limit=65)
                    df = pd.DataFrame(o, columns=['t','o','h','l','c','v'])
                    c = df['c']
                    m5, m20, m60 = c.rolling(5).mean().iloc[-1], c.rolling(20).mean().iloc[-1], c.rolling(60).mean().iloc[-1]
                    curr = c.iloc[-1]
                    
                    # [지침 4] 이격도 1.0% ~ 7.0% (사령관님 최적화 값)
                    gap = abs(m20 - m60) / m60 * 100
                    if 1.0 <= gap <= 7.0:
                        # 롱/숏 판정 로직
                        side = 'buy' if (m5 > m20 > m60 and curr > m5) else ('sell' if (m60 > m20 > m5 and curr < m5) else None)
                        
                        if side:
                            self.ex.set_leverage(self.leverage, s)
                            total_fire = bal * 0.95 # 잔고의 95% 할당
                            sl_p = curr * (1 - 0.0175) if side == 'buy' else curr * (1 + 0.0175) # ROE -35% 지점
                            
                            # --- [지침 5] 1차 사격 (3분할 중 1단계) ---
                            amt1 = float(self.ex.amount_to_precision(s, (total_fire / 3 * self.leverage) / curr))
                            self.ex.create_market_order(s, side, amt1)
                            self.log(f"🎯 {s} 1차 {side} 진입 (이격: {gap:.2f}%)")

                            failed = False
                            # --- [지침 6] 노 물타기 3분할 (방향 맞을 때만 후속탄) ---
                            for i in range(2, 4):
                                time.sleep(2) # 2초 간격 체크
                                now_p = self.ex.fetch_ticker(s)['last']
                                
                                # 1차 사격 후 즉시 손절가 터치 시 중단
                                if (side == 'buy' and now_p <= sl_p) or (side == 'sell' and now_p >= sl_p):
                                    self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', amt1, {'reduceOnly': True})
                                    self.log("🧨 방향 틀림! 1차 손절 후 작전 즉시 중단.")
                                    self.loss_count += 1
                                    failed = True
                                    break
                                
                                # 방향 맞으면 2차, 3차 투입
                                amt_next = float(self.ex.amount_to_precision(s, (total_fire / 3 * self.leverage) / now_p))
                                self.ex.create_market_order(s, side, amt_next)
                                self.log(f"📦 {i}차 후속 사격 완료.")

                            if failed: break 

                            # --- [지침 7] 익절 감시 (100% 반익절 + 1% 트레일링) ---
                            high_p, half_taken = now_p, False
                            while True:
                                time.sleep(3)
                                ticker = self.ex.fetch_ticker(s); now_p = ticker['last']
                                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == s]
                                c_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                                if c_amt == 0: break # 포지션 종료 시 루프 탈출
                                
                                roe = ((now_p - curr) / curr * 100 * self.leverage) if side == 'buy' else ((curr - now_p) / curr * 100 * self.leverage)
                                high_p = max(high_p, now_p) if side == 'buy' else min(high_p, now_p)

                                # 100% 수익 시 절반 익절
                                if not half_taken and roe >= 100:
                                    self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', c_amt / 2, {'reduceOnly': True})
                                    half_taken = True
                                    self.loss_count = 0 # 수익 나면 패배 카운트 리셋
                                    self.log("💰 100% 수익 달성! 절반 익절 및 패배 카운트 초기화.")

                                # 반익절 후 고점 대비 1% 하락 시 전량 익절 (트레일링)
                                if half_taken:
                                    drop = (high_p - now_p) / high_p * 100 if side == 'buy' else (now_p - high_p) / high_p * 100
                                    if drop >= 1.0:
                                        self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', c_amt, {'reduceOnly': True})
                                        self.log("🏁 트레일링 스탑 발동. 전량 익절 완료.")
                                        break
                                
                                # 최종 손절 라인 감시
                                if (side == 'buy' and now_p <= sl_p) or (side == 'sell' and now_p >= sl_p):
                                    self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', c_amt, {'reduceOnly': True})
                                    if not half_taken: self.loss_count += 1
                                    self.log("🚩 최종 손절 완료.")
                                    break
                            break # 거래 완료 후 대기
                time.sleep(15)
            except Exception as e:
                self.log(f"⚠️ 에러 발생: {e}")
                time.sleep(10)

if __name__ == "__main__":
    CommanderStrategyV80().run()
