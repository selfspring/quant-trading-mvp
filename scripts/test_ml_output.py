"""测试 ML 预测输出"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.signal_generator.ml_predictor import MLPredictor
import pandas as pd
import psycopg2

# 从数据库读 K 线
conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
df = pd.read_sql("SELECT time as timestamp, open, high, low, close, volume FROM kline_data WHERE symbol='au2606' AND interval='1m' ORDER BY time DESC LIMIT 100", conn)
conn.close()

if len(df) < 60:
    # 回退 AkShare
    import akshare as ak
    df = ak.futures_zh_minute_sina(symbol='au2606', period="1")
    df = df.tail(100).copy()
    df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'hold']
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

df = df.sort_values('timestamp').reset_index(drop=True)
print(f"K线数量: {len(df)}")

predictor = MLPredictor()
result = predictor.predict(df)

print(f"\n=== ML 预测结果 ===")
print(f"prediction (原始值): {result['prediction']}")
print(f"confidence: {result['confidence']}")
print(f"direction: {result['direction']}")
print(f"signal: {result['signal']}")
print(f"\n=== 置信度计算 ===")
print(f"abs(prediction) = {abs(result['prediction'])}")
print(f"abs(prediction) * 50 = {abs(result['prediction']) * 50}")
print(f"min(abs(prediction) * 50, 1.0) = {min(abs(result['prediction']) * 50, 1.0)}")
