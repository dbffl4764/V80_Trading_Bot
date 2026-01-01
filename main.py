import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_5M_Striker:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 10
        self.target_roe = 30.0  # 이 정도 수익나면 5일선 꺾일 때 익절 준비

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧬 {msg}", flush=True)

    def get_total_balance(self):
        try: return float(self.ex.fetch_balance()['total']['USDT'])
        except: return 0

    def check_v80_signal(self, symbol):
        """[5분봉 단독 검증] 잔파동 무시, 확실한 방향성 확정 시에만 진입"""
        try:
            # 5분봉 데이터 로드
            o5 = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=60)
            df5 = pd.DataFrame(o5, columns=['t', 'o', 'h', 'l', 'c', 'v'])

            # 이평선 계산 (5일, 20일, 60일)
            m5 = df5['c'].rolling(5).mean().iloc[-1]
            m20 = df5['c'].rolling(20).mean().iloc[-1]
            m60 = df5['c'].rolling(60).mean().iloc[-1]
            
            curr = df5['c'].iloc[-1]
            vol_avg = df5['v'].rolling(10).mean().iloc[-1]

            # 응축도: 20일선과 60일선이 5% 이내여야 함 (이미 쏟아진 건 안 잡음)
            ma_gap = abs(m20 - m60) / m60 * 100

            if ma_gap <= 5.0:
                # LONG: 5 > 20 > 60 (완벽 정배열) + 현재가가 5일선 위 + 거래량 동반
                if m5 > m20 > m60 and curr > m5 and df5['v'].iloc[-1] > vol_avg:
                    return "LONG", curr

                # SHORT: 60 > 20 > 5 (완벽 역배열) + 현재가가 5일선 아래 + 거래량 동반
                if m60 > m20 > m5 and curr < m5 and df5['v'].iloc[-1] > vol_avg:
                    return "SHORT", curr
            
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            total_bal = self.get_total_balance()
            # 3000불 기준 종목 수 조절 로직
            max_pos = 1 if total_bal < 3000 else 2
            firepower = (total_bal * 0.45) / max_pos
            amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [사격] {symbol} {side} 진입! (5M 방향성 확정)")

            # 손절가 설정 (약 -3.5% 가격 변동 시 손절)
            stop_p = float(self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035))
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, {'stopPrice': stop_p, 'reduceOnly': True})

            # 익절 감시 (ROE 30% 초과 후 5일선 이탈 시)
            while True:
                time.sleep(15)
                ticker = self.ex.fetch_ticker(symbol)
                curr = ticker['last']
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                
                if not pos or float(pos[0]['positionAmt']) == 0: 
                    self.log(f"🏁 {symbol} 포지션 종료 확인.")
                    break
                
                roe = ((curr - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * self.leverage)
                
                if roe > self.target_roe:
                    ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=5)
                    ma5 = pd.Series([x[4] for x in ohlcv]).mean()
                    if (side == "LONG" and curr < ma5) or (side == "SHORT" and curr > ma5):
                        self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', abs(float(pos[0]['positionAmt'])), {'reduceOnly': True})
                        self.log(f"💰 [수익확정] 차트 꺾임 감지 익절! ROE: {roe:.2f}%")
                        # 수익 30% 안전자산 이체 알림 (수동 이체 권장)
                        self.log(f"📢 원칙 알림: 수익금의 30%를 지금 바로 안전자산으로 옮기십시오!")
                        break
        except Exception as e: self.log(f"⚠️ 실행 에러: {e}")

    def run(self):
        self.log("⚔️ V80 5M STRIKER 가동. 확실한 5분봉 대세만 노립니다.")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                # 거래량 상위 20개 종목 중 변동성 5% 이상인 것만 정찰
                for s, t in sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:20]:
                    if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 5.0:
                        side, price = self.check_v80_signal(s)
                        if side: 
                            self.execute_mission(s, side, price)
                            break # 한 종목 진입 시 루프 탈출 후 집중 감시
                time.sleep(20) # 5분봉 관점이므로 정찰 간격도 여유 있게
            except Exception as e: 
                self.log(f"⚠️ 루프 에러: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_5M_Striker().run()
