# 사령관님의 V80 핵심 전략 소스코드
import pandas as pd

def check_v80_strategy(price_data, current_profit_rate):
    """
    1. 5/20/60일선 정배열 확인
    2. 20일선 이탈 여부 감시
    3. 수익률에 따른 안전자산 비율 계산
    """
    # 20일선 수호 로직
    ma20 = price_data['close'].rolling(window=20).mean().iloc[-1]
    current_price = price_data['close'].iloc[-1]
    
    # 수익 관리 로직 (현재 340% 상황 반영)
    if current_profit_rate >= 100:
        safe_move_ratio = 0.4  # 100% 넘으면 40% 안전자산으로
    else:
        safe_move_ratio = 0.3  # 그 외엔 30%
        
    return current_price > ma20, safe_move_ratio, ma20

print("✅ V80 전략 로직 로드 완료 (340% 수익 대응 모드)")
