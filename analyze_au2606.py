# -*- coding: utf-8 -*-
from quant.signal_generator.ml_predictor import MLPredictor
import pandas as pd
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='quant_trading',
    user='postgres',
    password='@Cmx1454697261'
)

# au2606 数据不足，使用 au_main 30m 数据
df = pd.read_sql("""
    SELECT time as timestamp, open, high, low, close, volume, 
           COALESCE(open_interest, 0) as open_interest 
    FROM kline_data 
    WHERE symbol='au_main' AND interval='30m' 
    ORDER BY time DESC 
    LIMIT 100
""", conn)

conn.close()

df = df.sort_values('timestamp').reset_index(drop=True)

print('Rows:', len(df))
print('Latest price:', float(df.iloc[-1]['close']))
print('Last5 closes:', df['close'].tail(5).tolist())

predictor = MLPredictor()
result = predictor.predict(df)

print('\n=== ML Prediction Result ===')
print('ML:', result)
