import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')

# au_main 30m data for technical analysis
df = pd.read_sql("""
    SELECT time as timestamp, open, high, low, close, volume, 
           COALESCE(open_interest, 0) as open_interest 
    FROM kline_data 
    WHERE symbol='au_main' AND interval='30m' 
    ORDER BY time DESC LIMIT 100
""", conn)

# au2606 latest 1m price
df_live = pd.read_sql("""
    SELECT time as timestamp, close 
    FROM kline_data 
    WHERE symbol='au2606' AND interval='1m' 
    ORDER BY time DESC LIMIT 5
""", conn)

conn.close()

print(f"au_main 30m rows: {len(df)}")
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n--- au2606 live ---")
if len(df_live) > 0:
    df_live = df_live.sort_values('timestamp')
    print(f"Latest price: {float(df_live.iloc[-1]['close'])}")
    print(f"Last5 1m: {df_live['close'].tolist()}")

print(f"\n--- au_main 30m ---")
print(f"Latest 30m close: {float(df.iloc[-1]['close'])}")
print(f"Last time: {df.iloc[-1]['timestamp']}")
print(f"Last5: {df['close'].tail(5).tolist()}")

# ML predictor
try:
    from quant.signal_generator.ml_predictor import MLPredictor
    predictor = MLPredictor()
    result = predictor.predict(df)
    print(f"\nML: {result}")
except Exception as e:
    print(f"\nML Error: {e}")

# Technical indicators
close = df['close'].astype(float)
ma5 = close.rolling(5).mean().iloc[-1]
ma10 = close.rolling(10).mean().iloc[-1]
ma20 = close.rolling(20).mean().iloc[-1]
last_price = float(close.iloc[-1])
prev_price = float(close.iloc[-2])

print(f"\nMA5: {ma5:.2f}, MA10: {ma10:.2f}, MA20: {ma20:.2f}")
print(f"Price vs MA5: {'ABOVE' if last_price > ma5 else 'BELOW'}")
print(f"Price vs MA20: {'ABOVE' if last_price > ma20 else 'BELOW'}")
print(f"MA5 vs MA20: {'BULLISH' if ma5 > ma20 else 'BEARISH'}")
print(f"Short momentum: {'UP' if last_price > prev_price else 'DOWN'}")

# RSI
delta = close.diff()
gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1]
loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
rsi = 100 - (100 / (1 + gain / loss)) if loss != 0 else 50
print(f"RSI(14): {rsi:.2f}")
