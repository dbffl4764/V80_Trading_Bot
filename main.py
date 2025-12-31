# main.py 수정 제안
if __name__ == "__main__":
    print("🚀 V80 전략 봇 가동! (100억 프로젝트 시작)")
    
    # 분석할 종목 리스트
    symbols = ['BTC/USDT', 'ETH/USDT']
    
    for symbol in symbols:
        print(f"🔍 {symbol} 분석 중...")
        signal = check_trend(exchange, symbol)  # v80_logic의 함수 호출
        print(f"📊 {symbol} 현재 신호: {signal}")
        
        if signal == "LONG":
            print(f"🔥 [진입 예정] 모든 추세 상승 정렬 완료!")
        elif signal == "SHORT":
            print(f"🔻 [진입 예정] 모든 추세 하락 정렬 완료!")
        else:
            print(f"⏳ [관망] 추세가 정렬되지 않았습니다.")
            
    print("🏁 분석 완료. 다음 스케줄에 다시 실행합니다.")
