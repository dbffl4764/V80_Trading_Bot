import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Dual_Striker:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 10
        self.target_roe = 30.0 # 이 정도 수익나면 5일선 꺾일 때 익절 준비

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧬 {msg}", flush=True)

    def get_total_balance(self):
        try: return float(self.ex.fetch_balance()['total']['USDT'])
        except: return 0

    def check_v80_signal(self, symbol):
        """[3분/5분 듀얼 검증] 가짜를 거르는 가장 신중한 로직"""
        try:
            # 3분봉과 5분봉 데이터 동시 로드
            o3 = self.ex.fetch_ohlcv(symbol, timeframe='3m', limit=60)
            o5 = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=60)
            
            df3 = pd.DataFrame(o3, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            df5 = pd.DataFrame(o5, columns=['t', 'o', 'h', 'l', 'c', 'v'])

            def get_mas(df):
                m5 = df['c'].rolling(5).mean()
                m20 = df['c'].rolling(20).mean()
                m60 = df['c'].rolling(60).mean()
                return m5.iloc[-1], m20.iloc[-1], m60.iloc[-1], m5.iloc[-2], m20.iloc[-2], m60.iloc[-1]

            m5_3, m20_3, m60_3, p5_3, p20_3, p60_3 = get_mas(df3)
            m5_5, m20_5, m60_5, p5_5, p20_5, p60_5 = get_mas(df5)
            curr = df3['c'].iloc[-1]
            vol_avg = df3['v'].rolling(10).mean().iloc[-1]

            # 응축도 (3분봉 기준 3.5% 이내)
            ma_gap = abs(m20_3 - m60_3) / m60_3 * 100

            if ma_gap <= 3.5:
                # LONG: 3분/5분 모두 정배열 초입 + 거래량 동반
                l3 = (p5_3 <= p20_3 and m5_3 > m20_3 > m60_3)
                l5 = (m5_5 > m20_5 > m60_5)
                if l3 and l5 and df3['v'].iloc[-1] > vol_avg:
                    return "LONG", curr

                # SHORT: 3분/5분 모두 역배열 초입 + 거래량 동반
                s3 = (p5_3 >= p20_3 and m60_3 > m20_3 > m5_3)
                s5 = (m60_5 > m20_5 > m5_5)
                if s3 and s5 and df3['v'].iloc[-1] > vol_avg:
                    return "SHORT", curr
            
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            total_bal = self.get_total_balance()
            max_pos = 1 if total_bal < 3000 else 2
            firepower = (total_bal * 0.45) / max_pos
            amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [사격] {symbol} {side} 진입! (3M/5M 동기화 완료)")

            # 손절가 설정 (-3.5% 가격변동 = 10배 기준 -35%)
            stop_p = float(self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035))
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, {'stopPrice': stop_p, 'reduceOnly': True})

            # 사령관님 방식의 '차트 꺾임' 익절 감시
            while True:
                time.sleep(15)
                ticker = self.ex.fetch_ticker(symbol)
                curr = ticker['last']
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                if not pos or float(pos[0]['positionAmt']) == 0: break
                
                # ROE 30% 이상일 때 5일선 이탈 시 익절
                roe = ((curr - entry_price) / entry_price * 100 * 10) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * 10)
                if roe > self.target_roe:
                    ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='3m', limit=5)
                    ma5 = pd.Series([x[4] for x in ohlcv]).mean()
                    if (side == "LONG" and curr < ma5) or (side == "SHORT" and curr > ma5):
                        self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', abs(float(pos[0]['positionAmt'])), {'reduceOnly': True})
                        self.log(f"🏁 [익절] 차트가 꺾여서 작전 종료합니다! ROE: {roe:.2f}%")
                        break
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log("⚔️ V80 DUAL STRIKER 가동. 3일 시뮬레이션 급 수익을 향해!")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                for s, t in sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:15]:
                    if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 5.0:
                        side, price = self.check_v80_signal(s)
                        if side: self.execute_mission(s, side, price); break
                time.sleep(10)
            except: time.sleep(5)

if __name__ == "__main__":
    V80_Dual_Striker().run()
