import json
import urllib.request

def run_v80():
    print("🚀 [V80 긴급 엔진] 가동!")
    # 바이낸스 공용 API 주소 (미국 서버에서도 잘 뚫리는 주소)
    url = "https://api1.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=30"
    
    try:
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
        
        # 종가 데이터만 추출
        closes = [float(day[4]) for day in data]
        price = closes[-1]
        
        # 20일 이동평균선 계산
        ma20 = sum(closes[-21:-1]) / 20
        
        print(f"📊 현재가: {price:.2f} | 20일선: {ma20:.2f}")
        
        if price > ma20:
            print(f"✅ 결과: 20일선 위 '안전'. (현재 수익 345% 지키는 중)")
        else:
            print("🚨🚨 경보: 20일선 이탈! 수익 40% 확정 준비!")
            
    except Exception as e:
        print(f"❌ 데이터 수집 오류: {e}")

if __name__ == "__main__":
    run_v80()
