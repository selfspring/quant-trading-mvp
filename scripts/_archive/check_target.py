import psycopg2, pandas as pd, numpy as np
from quant.signal_generator.feature_engineer import FeatureEngineer

conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
df = pd.read_sql('SELECT time as timestamp, symbol, interval, open, high, low, close, volume, open_interest FROM kline_data WHERE symbol=\'au9999\' AND interval=\'15m\' ORDER BY time LIMIT 1000', conn)
conn.close()

for c in ['open','high','low','close','volume','open_interest']:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df['symbol'] = 'au9999'
df['interval'] = '15m'

fe = FeatureEngineer()
df_feat = fe.generate_features(df)
print(f'Features shape: {df_feat.shape}')
print(f'Feature cols: {[c for c in df_feat.columns if c not in ["timestamp","symbol","interval","open","high","low","close","volume","open_interest"]][:5]}')

horizon = 60
df_feat['target'] = np.log(df_feat['close'].shift(-horizon) / df_feat['close'])
print('Target stats:')
print(df_feat['target'].describe())
print(f'Positive: {(df_feat["target"] > 0).sum()}, Negative: {(df_feat["target"] < 0).sum()}')
