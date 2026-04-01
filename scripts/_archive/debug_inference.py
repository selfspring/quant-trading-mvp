import sys, numpy as np, pandas as pd
sys.path.insert(0, r'E:\quant-trading-mvp')
import lightgbm as lgb
import psycopg2
from quant.signal_generator.feature_engineer import FeatureEngineer

# 加载模型
model = lgb.Booster(model_file=r'models\lgbm_model.txt')
model_features = model.feature_name()
print(f'Model expects {len(model_features)} features: {model_features[:10]}...')

# 加载最新 K 线
conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
df = pd.read_sql(
    "SELECT time as timestamp, open, high, low, close, volume, open_interest "
    "FROM kline_data WHERE symbol='au2606' AND interval='1m' ORDER BY time DESC LIMIT 200",
    conn
)
conn.close()
df = df.iloc[::-1].reset_index(drop=True)
for c in ['open','high','low','close','volume','open_interest']:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df['symbol'] = 'au2606'
df['interval'] = '1m'
print(f'Latest bar: {df.iloc[-1]["timestamp"]} close={df.iloc[-1]["close"]}')

# 生成特征
fe = FeatureEngineer()
df_feat = fe.generate_features(df)
print(f'Generated {len(df_feat.columns)} feature cols')

# 取最新一行
latest = df_feat.iloc[-1]

# 检查特征对齐
missing = [f for f in model_features if f not in df_feat.columns]
extra = [f for f in df_feat.columns if f not in model_features and f not in ['timestamp','symbol','interval','open','high','low','close','volume','open_interest']]
print(f'Missing features: {missing}')
print(f'Extra features (ignored): {extra[:5]}')

# 构造输入
feature_values = []
for f in model_features:
    val = latest.get(f, np.nan)
    feature_values.append(float(val) if pd.notna(val) else 0.0)

X = np.array(feature_values).reshape(1, -1)
pred = model.predict(X)[0]
print(f'\nPrediction: {pred:.6f}')
print(f'abs(pred): {abs(pred):.6f}')
print(f'Signal: {"buy" if pred > 0.0015 else "sell" if pred < -0.0015 else "hold"}')

# 检查 NaN 特征
nan_feats = [(f, v) for f, v in zip(model_features, feature_values) if np.isnan(v) or v == 0.0]
print(f'\nZero/NaN features ({len(nan_feats)}): {nan_feats[:10]}')
