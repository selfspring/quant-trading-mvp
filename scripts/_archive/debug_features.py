import psycopg2, pandas as pd, numpy as np
import sys
sys.path.insert(0, r'E:\quant-trading-mvp')
from quant.signal_generator.feature_engineer import FeatureEngineer

conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
df = pd.read_sql('SELECT time as timestamp, symbol, interval, open, high, low, close, volume, open_interest FROM kline_data WHERE symbol=\'au9999\' AND interval=\'15m\' ORDER BY time LIMIT 200', conn)
conn.close()

for c in ['open','high','low','close','volume','open_interest']:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df['symbol'] = 'au9999'
df['interval'] = '15m'

print('Input df columns:', list(df.columns))
print('Input df shape:', df.shape)
print('Input df dtypes:', df.dtypes.to_dict())
print('Input sample:')
print(df.head(3).to_string())

fe = FeatureEngineer()
df_feat = fe.generate_features(df)
print('\nOutput shape:', df_feat.shape)

# Check NaN ratio per column
nan_ratio = df_feat.isnull().mean()
high_nan = nan_ratio[nan_ratio > 0.5]
print(f'\nCols with >50% NaN: {len(high_nan)}')
print(high_nan.head(20))

# Check target
horizon = 4
df_feat['target'] = np.log(df_feat['close'].shift(-horizon) / df_feat['close'])
clean = df_feat.dropna()
print(f'\nClean rows after dropna: {len(clean)}')
