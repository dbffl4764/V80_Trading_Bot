import json
import urllib.request

def run_v80():
    print("🚀 [V80 무적 우회 엔진] 가동!")
    # 바이낸스 대신 야후 파이낸스 데이터 소스 사용 (차단 불가)
    url = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1d&range=30d"
    
    headers = {'User-Agent': 'Mozilla/5.0'} # 사람인 척 하기
    
    try:
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())
        
        # 야후 파이낸스 데이터 구조에서 가격 추출
        result = data['chart']['result'][0]
        closes = result['indicators']['quote'][0]['close']
        
        # None 값 제거 및 현재가 추출
        closes = [x for x in closes if x is not None]
        price = closes[-1]
        
        # 20일 이동평균선 계산
        ma20 = sum(closes[-21:-1]) / 20
        
        print(f"📊 [야후금융 데이터] 현재가: {price:.2f} | 20일선: {ma20:.2f}")
        
        if price > ma20:
            print(f"✅ 결과: 20일선 위 '안전'. (수익 345% 홀딩 중!)")
        else:
            print("🚨🚨 경보: 20일선 이탈! 사령관님, 수익 40% 확보하세요!")
            
    except Exception as e:
        print(f"❌ 데이터 수집 오류: {e}")

if __name__ == "__main__":
    run_v80()
