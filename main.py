import ccxt, time, os, pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_AI_Brain:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'), 'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'}, 'enableRateLimit': True
        })
        self.leverage = 5  # [지침] 2000불까지 5배 고정
        self.log_file = "trading_data.csv"
        
        # [AI 기본값] 학습 전 기본 세팅
        self.best_gap_max = 7.0
        self.min_vol_filter = 100000000

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧠 {msg}", flush=True)

    def learn_from_data(self):
        """[AI 학습 및 적용] 과거 데이터를 분석하여 진입 필터 보정"""
        if not os.path.exists(self.log_file): return
        
        try:
            df = pd.read_csv(self.log_file)
            if len(df) < 5: return # 최소 5번의 데이터가 쌓여야 학습 시작

            # 승리한 매매와 패배한 매매의 이격도 평균 분석
            win_trades = df[df['result'] == 'Win']
            loss_trades = df[df['result'] == 'Loss']
            
            if len(loss_trades) > 0:
                # 손절이 났을 때의 평균 이격도보다 10% 낮게 필터 보정 (보수적 접근)
                avg_loss_gap = loss_trades['gap'].mean()
                self.best_gap_max = min(7.0, round(avg_loss_gap * 0.9, 2))
                self.log(f"🤖 AI 보정 완료: 최적 이격도 상한을 {self.best_gap_max}%로 하향 조정")
        except:
            pass

    def run(self):
        self.log("🚀 [AI 자가학습 엔진] 가동. 13불로 데이터를 먹이며 성장합니다.")
        while True:
            try:
                # 1. 매 사이클마다 데이터 학습 후 필터 업데이트
                self.learn_from_data()
                
                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 5: break

                ts = self.ex.fetch_tickers()
                # 2. AI가 학습한 최소 거래량 및 변동성 필터 적용
                targets = [s for s, t in ts.items() if s.endswith('/USDT:USDT') and 'BTC' not in s 
                           and abs(t.get('percentage', 0)) >= 10.0 and t.get('quoteVolume', 0) >= self.min_vol_filter]
                
                for s in sorted(targets, key=lambda x: ts[x].get('quoteVolume', 0), reverse=True)[:5]:
                    # 1H 확증 로직 (사령관님 표 지침)
                    o_1h = self.ex.fetch_ohlcv(s, '1h', limit=70); df_1h = pd.DataFrame(o_1h, columns=['t','o','h','l','c','v'])
                    side_1h = 'buy' if (df_1h['c'].rolling(5).mean().iloc[-1] > df_1h['c'].rolling(20).mean().iloc[-1] > df_1h['c'].rolling(60).mean().iloc[-1]) else \
                              ('sell' if (df_1h['c'].rolling(60).mean().iloc[-1] > df_1h['c'].rolling(20).mean().iloc[-1] > df_1h['c'].rolling(5).mean().iloc[-1]) else None)
                    if not side_1h: continue

                    # 5M 정밀 타격
                    o_5m = self.ex.fetch_ohlcv(s, '5m', limit=70); df_5m = pd.DataFrame(o_5m, columns=['t','o','h','l','c','v'])
                    c_5m = df_5m['c']; m5, m20, m60 = c_5m.rolling(5).mean().iloc[-1], c_5m.rolling(20).mean().iloc[-1], c_5m.rolling(60).mean().iloc[-1]
                    gap_60_20 = abs(m60 - m20) / m60 * 100
                    curr = c_5m.iloc[-1]

                    # 3. [AI 피드백 적용] 학습된 gap_max 이내일 때만 진입
                    if (1.0 <= gap_60_20 <= self.best_gap_max) and \
                       ((side_1h == 'buy' and curr > m5 and curr > df_5m['h'].iloc[-2]) or \
                        (side_1h == 'sell' and curr < m5 and curr < df_5m['l'].iloc[-2])):
                        
                        # [진입 및 데이터 기록 로직 수행...]
                        # (중략: 진입 후 결과(Win/Loss)를 csv에 저장)
                        self.log(f"🎯 AI 승인 타점 포착: {s} (이격 {gap_60_20:.2f}%)")
                        break
                time.sleep(30)
            except:
                time.sleep(10)
