import ccxt
import time
import os
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드 (API KEY 보호)
load_dotenv()

class V80_Final_War:
    def __init__(self):
        # 1. 바이낸스 선물 연결
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 20
        self.loss_count = 0 
        self.safety_limit = 2000.0  # 2000불 미만 2분할 사격 지침
        self.target_profit_roe = 100.0 # 100% ROE 반익절

    def log(self, msg):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🛡️ {msg}", flush=True)

    def get_market_data(self, symbol, timeframe='5m', limit=100):
        """OHLCV 데이터 수집 및 이평선 계산"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            df['ma5'] = df['c'].rolling(5).mean()
            df['ma20'] = df['c'].rolling(20).mean()
            df['ma60'] = df['c'].rolling(60).mean()
            return df
        except:
            return None

    def run(self):
        self.log("🚀 [사령관님 5년 연구 결집] 47불 부활 작전 엔진 가동!")
        
        while True:
            try:
                # [지침 7] 하루 3번 손절 시 당일 셧다운
                if self.loss_count >= 3:
                    self.log("❌ [경고] 금일 3패 달성. 사령관님 지침에 따라 작전을 종료합니다."); break

                # 잔고 확인
                bal_info = self.ex.fetch_balance()
                usdt_balance = float(bal_info['total']['USDT'])
                if usdt_balance < 10:
                    self.log("⚠️ 시드 고갈. 작전 불가능."); break

                # [지침 2, 3] 종목 선정 (비트 제외, 변동성 10% 이상, 거래량 상위 10개)
                tickers = self.ex.fetch_tickers()
                targets = [
                    s for s, t in tickers.items() 
                    if s.endswith('/USDT:USDT') and 'BTC' not in s and abs(t.get('percentage', 0)) >= 10.0
                ]
                targets = sorted(targets, key=lambda x: tickers[x].get('quoteVolume', 0), reverse=True)[:10]

                for symbol in targets:
                    df = self.get_market_data(symbol)
                    if df is None or len(df) < 60: continue

                    curr_price = df['c'].iloc[-1]
                    m5, m20, m60 = df['ma5'].iloc[-1], df['ma20'].iloc[-1], df['ma60'].iloc[-1]
                    
                    # [사령관님 핵심 로직 1] 60-20-5 이평선 정렬 확인
                    # [사령관님 핵심 로직 2] 60-20 이격도 (1~7%) 수렴 확인
                    gap_60_20 = abs(m60 - m20) / m60 * 100
                    
                    side = None
                    if (m5 > m20 > m60) and (1.0 <= gap_60_20 <= 7.0) and (curr_price > m5):
                        side = 'buy'
                    elif (m60 > m20 > m5) and (1.0 <= gap_60_20 <= 7.0) and (curr_price < m5):
                        side = 'sell'

                    if side:
                        # 레버리지 설정
                        self.ex.set_leverage(self.leverage, symbol)
                        
                        # [지침 5] 2000불 미만 2분할 사격
                        max_division = 2 if usdt_balance < self.safety_limit else 3
                        # 한 발당 수량 (수수료 대비 0.9 곱함)
                        qty = float(self.ex.amount_to_precision(symbol, (usdt_balance * 0.9 * self.leverage / max_division) / curr_price))
                        
                        # [지침 6] 진입과 동시에 1.75% 스탑로스 설정
                        sl_price = float(self.ex.price_to_precision(symbol, curr_price * (1 - 0.0175) if side == 'buy' else curr_price * (1 + 0.0175)))

                        # 1차 진입
                        self.log(f"🎯 {symbol} {side} 1차 사격! 이격도: {gap_60_20:.2f}%")
                        self.ex.create_market_order(symbol, side, qty)
                        
                        # 즉시 스탑로스 주문 (서버에 직접 박음)
                        self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == 'buy' else 'buy', qty * max_division, None, {
                            'stopPrice': sl_price, 'reduceOnly': True
                        })

                        # [지침] 수익 중일 때만 2차 후속탄 (불타기)
                        time.sleep(10)
                        current_ticker = self.ex.fetch_ticker(symbol)
                        if (side == 'buy' and current_ticker['last'] > curr_price) or (side == 'sell' and current_ticker['last'] < curr_price):
                            self.ex.create_market_order(symbol, side, qty)
                            self.log(f"📦 {symbol} 2차 후속탄 투입 완료.")

                        # 익절 관리 루프
                        highest_price, half_sold = current_ticker['last'], False
                        while True:
                            time.sleep(10)
                            pos_info = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'] == symbol.replace('/', '').replace(':USDT', '')]
                            amt = abs(float(pos_info[0]['positionAmt'])) if pos_info else 0
                            
                            if amt == 0: # 손절 혹은 익절 완료됨
                                self.ex.cancel_all_orders(symbol)
                                if not half_sold: self.loss_count += 1
                                break
                            
                            p_now = self.ex.fetch_ticker(symbol)['last']
                            roe = ((p_now - curr_price) / curr_price * 100 * self.leverage) if side == 'buy' else ((curr_price - p_now) / curr_price * 100 * self.leverage)
                            highest_price = max(highest_price, p_now) if side == 'buy' else min(highest_price, p_now)

                            # [지침 9] 100% ROE 달성 시 50% 익절
                            if not half_sold and roe >= self.target_profit_roe:
                                self.ex.create_market_order(symbol, 'sell' if side == 'buy' else 'buy', amt / 2, {'reduceOnly': True})
                                half_sold = True
                                self.loss_count = 0 # 패배 카운트 리셋
                                self.log(f"💰 {symbol} 100% ROE 달성! 50% 익절 완료.")

                            # [지침 10] 트레일링 스탑 (최고가 대비 1% 하락 시 전량 매도)
                            if half_sold:
                                pull_back = (highest_price - p_now) / highest_price * 100 if side == 'buy' else (p_now - highest_price) / highest_price * 100
                                if pull_back >= 1.0:
                                    self.ex.create_market_order(symbol, 'sell' if side == 'buy' else 'buy', amt, {'reduceOnly': True})
                                    self.log(f"🏁 {symbol} 트레일링 스탑 발동. 작전 종료."); break
                        break
                time.sleep(30)
            except Exception as e:
                self.log(f"⚠️ 시스템 오류 발생: {e}"); time.sleep(20)

if __name__ == "__main__":
    V80_Final_War().run()
