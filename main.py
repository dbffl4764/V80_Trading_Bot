import os
import ccxt
import pandas as pd

def run_v80_unified():
    print("🚀 [V80 통합 엔진] 가동!")
    
    # 비트겟 연동
    bg_key = os.environ.get('BITGET_API_KEY')
    bg_sec = os.environ.get('BITGET_SECRET_KEY')
    bg_pas = os.environ.get('BITGET_PASSPHRASE')
    
    if bg_key:
        try:
            bg = ccxt.bitget({'apiKey': bg_key, 'secret': bg_sec, 'password': bg_pas, 'options': {'defaultType': 'future'}})
            bal = bg.fetch_balance()
            total = bal['total'].get('USDT', 0)
            print(f"💰 [비트겟 잔고] {total:,.2f} USDT")
            # 수익 30% 원칙 (301.90불 기준 약 90불 권고 출력)
            if total > 200:
                print(f"⚠️ [수익 관리] 안전자산 {total * 0.3:,.2f} USDT 회수 대상")
        except Exception as e:
            print(f"❌ 비트겟 연결 실패: {e}")

    # 바이낸스 연동
    bn_key = os.environ.get('BINANCE_KEY')
    bn_sec = os.environ.get('BINANCE_SECRET')
    if bn_key:
        try:
            bn = ccxt.binance({'apiKey': bn_key, 'secret': bn_sec, 'options': {'defaultType': 'future'}})
            bal = bn.fetch_balance()
            print(f"💰 [바이낸스 잔고] {bal['total'].get('USDT', 0):,.2f} USDT")
        except Exception as e:
            print(f"❌ 바이낸스 연결 실패: {e}")

if __name__ == "__main__":
    run_v80_unified()
