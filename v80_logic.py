cat << 'EOF' > v80_logic.py
import pandas as pd

def check_logic(df_d, df_m):
    # 일봉(1D) 60-20 이격도 계산
    ma60 = df_d['c'].rolling(60).mean().iloc[-1]
    ma20 = df_d['c'].rolling(20).mean().iloc[-1]
    curr = df_d['c'].iloc[-1]
    disparity = abs(ma20 - ma60) / ma60 * 100
    
    # 5분봉(5M) 단기 정렬 확인
    m_ma20 = df_m['c'].rolling(20).mean().iloc[-1]
    
    if disparity >= 3.0: # 이격도 3% 이상
        if curr > ma20 and curr > m_ma20: return "LONG"
        if curr < ma20 and curr < m_ma20: return "SHORT"
    return None
EOF
