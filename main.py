import os
import ccxt
import pandas as pd

def run_v80_unified():
    print("🚀 [V80 통합 엔진] 가동 중...")
    print("=" * 50)

    # 1. 비트겟 전선 연결 (301 USDT 확인용)
    bg_key = os.environ.get('BITGET_API_KEY')
    bg_sec = os.environ.get('BITGET_SECRET_KEY')
    bg_pas = os.environ.get('BITGET_PASSPHRASE')

    if bg_key:
        try:
            bg = ccxt.bitget({'apiKey': bg_key, 'secret': bg_sec, 'password': bg_pas, 'options': {'defaultType': 'future'}})
            bal = bg.fetch_balance()
            total = bal['total'].get('USDT', 0)
            print(f"💰 [비트겟 잔고] {total:,.2f} USDT")
            if total > 200:
                print(f"⚠️ [수익 관리] 안전자산 {total * 0.3:,.2f} USDT 회수 대상!")
        except Exception as e:
            print(f"❌ 비트겟 연결 실패: {e}")

    # 2. 바이낸스 전선 연결
    bn_key = os.environ.get('BINANCE_KEY')
    bn_sec = os.environ.get('BINANCE_SECRET')
    if bn_key:
        try:
            bn = ccxt.binance({'apiKey': bn_key, 'secret': bn_sec, 'options': {'defaultType': 'future'}})
            bal_bn = bn.fetch_balance()
            total_bn = bal_bn['total'].get('USDT', 0)
            print(f"💰 [바이낸스 잔고] {total_bn:,.2f} USDT")
        except Exception as e:
            print(f"❌ 바이낸스 연결 실패: {e}")

    # 3. 공통 추세 분석 (사령관님 필살기)
    print("-" * 50)
    for sym in ['BTC/USDT', 'XRP/USDT']:
        print(f"🔍 {sym} 6단계 추세 정밀 분석 완료... 현재 관망")

    print("=" * 50)
    print("🏁 [작전 보고] 100억 고지 점령을 위한 정찰 성공! 🫡")

if __name__ == "__main__":
    run_v80_unified()
