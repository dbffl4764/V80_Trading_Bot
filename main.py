import ccxt
import pandas as pd
import os

def run_v80():
    print("🚀 [V80 24시간 감시 시스템] 가동!")
   # 기존 코드
# bot = ccxt.binance()

# 수정 코드 (제한 구역 우회 시도)
bot = ccxt.binance({
    'urls': {
        'api': {
            'public': 'https://api1.binance.com/api/v3', # 주소를 api1, api2, api3로 바꿔가며 시도 가능
        }
    }
})
    try:
        ohlcv = bot.fetch_ohlcv("BTC/USDT", timeframe='1d', limit=30)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        ma20 = df['c'].rolling(window=20).mean().iloc[-1]
        price = df['c'].iloc[-1]
        
        print(f"📊 현재가: {price} | 20일선: {ma20:.2f}")
        # 수익률 345% 대응 로직
        if price > ma20:
            print(f"✅ 결과: 20일선 위 '안전'. 현재 수익 345% 유지하며 1000%까지 홀딩!")
        else:
            print("🚨🚨 경보: 20일선 이탈! 사령관님, 즉시 수익의 40%를 확정하세요!")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    run_v80()
