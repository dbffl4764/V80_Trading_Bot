import os
import ccxt
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path='/home/dbffl4764/V80_Trading_Bot/.env')

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

MAJORS_KEYWORDS = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'LINK', 'SUI', 'APT']

def get_dynamic_watchlist(exchange, total_balance):
    try:
        tickers = exchange.fetch_tickers()
        volatile_candidates = []
        
        for symbol, t in tickers.items():
            if 'USDT' in symbol and ":" not in symbol:
                # 1. 24시간 등락률 확인
                pct = t.get('percentage', 0)
                
                # 2. [추가] 오늘 저가 대비 등락률 확인 (실시간 급등주 포착)
                low = t.get('low', 0)
                last = t.get('last', 0)
                low_to_last_pct = ((last - low) / low * 100) if low > 0 else 0
                
                # 둘 중 하나라도 15% 이상이면 후보군 등록 ㅡㅡ;ㅋ
                max_change = max(abs(pct), low_to_last_pct)
                
                if max_change >= 15:
                    if total_balance < 3000:
                        if any(m in symbol for m in MAJORS_KEYWORDS):
                            continue
                    volatile_candidates.append({'symbol': symbol, 'change': max_change})

        sorted_list = sorted(volatile_candidates, key=lambda x: x['change'], reverse=True)
        return [m['symbol'] for m in sorted_list[:15]]
    except Exception as e:
        print(f"⚠️ 리스트 생성 에러: {e}")
        return []

# (check_v80_signal, execute_v80_trade 함수는 이전 통합본과 동일하게 유지)
