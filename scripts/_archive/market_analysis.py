import pandas as pd
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

from quant.signal_generator.ml_predictor import MLPredictor
from quant.common.config import config
from quant.common.db import db_engine

with db_engine(config) as engine:
    # 使用 1m 数据，获取至少 200 条
    df = pd.read_sql("SELECT time as timestamp, open, high, low, close, volume, COALESCE(open_interest, 0) as open_interest FROM kline_data WHERE symbol='au2606' AND interval='1m' ORDER BY time DESC LIMIT 200", engine)
df = df.sort_values('timestamp').reset_index(drop=True)

print(f'Data rows: {len(df)}')
print(f'Latest time: {df.iloc[-1]["timestamp"]}')

predictor = MLPredictor()
result = predictor.predict(df)
print('ML:', result)
print('Price:', float(df.iloc[-1]['close']))
print('Last5:', df['close'].tail(5).tolist())
