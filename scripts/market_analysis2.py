import pandas as pd
import psycopg2
import sys

sys.path.insert(0, 'E:/quant-trading-mvp')

conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')

# au2606 1m data for latest price
df_1m = pd.read_sql("""SELECT time as timestamp, open, high, low, close, volume, COALESCE(open_interest, 0) as open_interest 
    FROM kline_data WHERE symbol='au2606' AND interval='1m' 
    ORDER BY time DESC LIMIT 50""", conn)

# au_main 30m data for ML prediction
df_30m = pd.read_sql("""SELECT time as timestamp, open, high, low, close, volume, COALESCE(open_interest, 0) as open_interest 
    FROM kline_data WHERE symbol='au_main' AND interval='30m' 
    ORDER BY time DESC LIMIT 100""", conn)

conn.close()

df_1m = df_1m.sort_values('timestamp').reset_index(drop=True)
df_30m = df_30m.sort_values('timestamp').reset_index(drop=True)

print(f'au2606 1m rows: {len(df_1m)}')
print(f'au_main 30m rows: {len(df_30m)}')

if len(df_1m) > 0:
    print(f'Latest price (au2606): {float(df_1m.iloc[-1]["close"])}')
    print(f'Last5 (au2606 1m): {df_1m["close"].tail(5).tolist()}')
    print(f'Latest time: {df_1m.iloc[-1]["timestamp"]}')

if len(df_30m) >= 10:
    from quant.signal_generator.ml_predictor import MLPredictor
    predictor = MLPredictor()
    result = predictor.predict(df_30m)
    print(f'ML result: {result}')
else:
    print('Not enough 30m data for ML')
