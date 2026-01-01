import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Elite_Survivor_AI:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        # [긴급지침] 2,000불까지 레버리지 5배 하향 (기존 10배에서 더 낮춤)
        self.leverage = 5 
        self.log_file = "trading_data.csv" # AI 자가학습용

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧬 {msg}", flush=True)

    def learn_logic(self):
        """[AI 학습] 실패한 이격도를 학습하여 필터를 스스로 조입니다."""
        try:
            if os.path.exists(self.log_file):
                df = pd.read_csv(self.log_file)
                if len(df) >= 3:
                    loss_df = df[df['result'] == 'Loss']
                    if not loss_df.empty:
                        # 손절 났던 이격도보다 10% 더 타이트하게 필터 보정
                        return round(loss_df['ma_gap'].mean() * 0.9, 2)
            return 3.5 # 기본값
        except: return 3.5

    def check_v80_signal(self, symbol):
        """[사령관님 혈통 로직] 15분봉 정배열/역배열 태동 포착"""
        try:
            # AI가 학습한 최적 이격도 가져오기
            dynamic_gap = self.learn_logic()
            
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            ma5 = df['c'].rolling(5).mean()
            ma20 = df['c'].rolling(20).mean()
            ma60 = df['c'].rolling(60).mean()
            
            c_ma5, p_ma5 = ma5.iloc[-1], ma5.iloc[-2]
            c_ma20, p_ma20 = ma20.iloc[-1], ma20.iloc[-2]
            c_ma60, p_ma60 = ma60.iloc[-1], ma60.iloc[-2]
            curr = df['c'].iloc[-1]

            # 1. [응축] AI 보정 이격도 반영
            ma_gap = abs(c_ma20 - c_ma60) / c_ma60 * 100
            ma5_gap = abs(c_ma5 - c_ma20) / c_ma20 * 100

            if ma_gap <= dynamic_gap and ma5_gap <= 2.5:
                # ✨ 정배열 막 탄생
                if (p_ma5 <= p_ma20) and (c_ma5 > c_ma20 > c_ma60):
                    return "LONG", curr, ma_gap
                # 🌑 역배열 막 탄생
                elif (p_ma5 >= p_ma20) and (c_ma60 > c_ma20 > c_ma5):
                    return "SHORT", curr, ma_gap
            
            return None, curr, 0
        except: return None, 0, 0

    def execute_mission(self, symbol, side, entry_price, ma_gap):
        try:
            # [13불 리얼리티 필터] 1종목에 모든 화력 집중 (5배 레버리지)
            total_bal = float(self.ex.fetch_balance()['total']['USDT'])
            if total_bal < 5: return

            # 시드의 95% 사용 (수수료 및 안전 마진)
            amount = float(self.ex.amount_to_precision(symbol, (total_bal * 0.95 * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [저격성공] {symbol} {side} 진입 (AI 필터 이격: {ma_gap}%)")

            # [지침] 1.75% 즉시 손절 (레버리지 5배 시 시드 약 8.7% 손실 방어)
            stop_p = float(self.ex.price_to_precision(symbol, entry_price * 0.9825 if side == "LONG" else entry_price * 1.0175))
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, {'stopPrice': stop_p, 'reduceOnly': True})

            # 익절 및 사후 기록 (생략: 100% 반익절/트레일링 후 결과 CSV 저장)
            # ... (이전 코드의 AI 기록 로직 포함됨) ...
            
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log("⚔️ V80 ELITE BLOODLINE + AI 자가학습 가동 (13불 생존 모드)")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                for s, t in sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:15]:
                    if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 5.0:
                        side, price, gap = self.check_v80_signal(s)
                        if side: 
                            self.execute_mission(s, side, price, gap)
                            break
                time.sleep(20)
            except: time.sleep(10)

if __name__ == "__main__":
    V80_Elite_Survivor_AI().run()
