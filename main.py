import pandas as pd
import yfinance as yf
import time

def run_v80():
    print("🚀 [V80 무적 우회 감시 시스템] 가동!")
    try:
        # 비트코인 데이터를 야후 파이낸스에서 가져옴 (차단 걱정 없음)
        btc = yf.Ticker("BTC-USD")
        df = btc.history(period="60d", interval="1d")
        
        if df.empty:
            print("⚠️ 데이터를 가져오지 못했습니다.")
            return

        # 20일 이동평균선 계산
        ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
        price = df['Close'].iloc[-1]
        
        print(f"📊 현재가: {price:.2f} | 20일선: {ma20:.2f}")
        
        # 사령관님의 345% 수익 수호 전략
        if price > ma20:
            print(f"✅ 결과: 20일선 위 '안전'. (수익 345% 유지하며 1000%까지 홀딩!)")
        else:
            print("🚨🚨 경보: 20일선 이탈! 사령관님, 즉시 수익의 40%를 확정하세요!")
            
    except Exception as e:
        print(f"❌ 데이터 수집 오류: {e}")

if __name__ == "__main__":
    run_v80()
