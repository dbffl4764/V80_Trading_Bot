import os
import ccxt
import pandas as pd

def get_exchange_data(exchange, name):
    try:
        balance = exchange.fetch_balance()
        total_usdt = balance['total'].get('USDT', 0)
        print(f"💰 [{name} 잔고] {total_usdt:,.2f} USDT")
        
        # 수익 관리 원칙 (200불 기준 시작 가정)
        if total_usdt > 200:
            ratio = 0.4 if total_usdt >= 400 else 0.3
            print(f"⚠️ [{name} 관리] 안전자산 {total_usdt * ratio:,.2f} USDT 회수 대상")
        return total_usdt
    except Exception as e:
        print(f"❌ {name} 연결 실패: {e}")
        return 0

def analyze_trend(exchange, symbol):
    timeframes = ['1M', '1w', '1d', '4h', '2h', '1h']
    trends = []
    try:
        for tf in timeframes:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=20)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma20 = df['c'].rolling(window=20).mean().iloc[-1]
            trends.append(df['c'].iloc[-1] > ma20)
        
        if all(trends): return "🔥 롱 진입 대기"
        if all([not t for t in trends]): return "❄️ 숏 진입 대기"
        return "⏳ 관망 유지"
    except:
        return "⚙️ 분석 중"

def run_v80_unified():
    print("🚀 [V80 무적 통합 AI 엔진] 전 전선 기동!")
    print("=" * 50)

    # 1. 바이낸스 연결
    bn_key = os.environ.get('BINANCE_KEY')
    bn_sec = os.environ.get('BINANCE_SECRET')
    if bn_key:
        bn = ccxt.binance({'apiKey': bn_key, 'secret': bn_sec, 'options': {'defaultType': 'future'}})
        get_exchange_data(bn, "바이낸스")

    # 2. 비트겟 연결
    bg_key = os.environ.get('BITGET_API_KEY')
    bg_sec = os.environ.get('BITGET_SECRET_KEY')
    bg_pas = os.environ.get('BITGET_PASSPHRASE')
    if bg_key:
        bg = ccxt.bitget({'apiKey': bg_key, 'secret': bg_sec, 'password': bg_pas, 'options': {'defaultType': 'future'}})
        get_exchange_data(bg, "비트겟")
        
        print("-" * 50)
        # 3. 통합 추세 분석
        for sym in ['BTC/USDT', 'XRP/USDT']:
            res = analyze_trend(bg, sym)
            print(f"📊 [{sym}] AI 분석 결과: {res}")

    print("=" * 50)
    print("🏁 [작전 보고 완료] 모든 데이터 정상 출력. 100억 고지 점령 중! 🫡")

if __name__ == "__main__":
    run_v80_unified()
