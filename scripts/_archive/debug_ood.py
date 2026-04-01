import sys
sys.path.insert(0, r'E:\quant-trading-mvp')
import psycopg2, pandas as pd, numpy as np
import lightgbm as lgb
from quant.signal_generator.feature_engineer import FeatureEngineer

# 加载模型
model = lgb.Booster(model_file=r'models\lgbm_model_au9999.txt' if __import__('os').path.exists(r'models\lgbm_model_au9999.txt') else r'models\lgbm_model.txt')
model_features = model.feature_name()
print(f'Model features: {len(model_features)}')

# 获取 au2606 推理数据
conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading', user='postgres', password='@Cmx1454697261')
df = pd.read_sql('SELECT time as timestamp, symbol, interval, open, high, low, close, volume, open_interest FROM kline_data WHERE symbol=\'au2606\' AND interval=\'30m\' ORDER BY time DESC LIMIT 200', conn)

# 获取 au9999 训练数据最后200行做对比
df_train = pd.read_sql('SELECT time as timestamp, symbol, interval, open, high, low, close, volume, open_interest FROM kline_data WHERE symbol=\'au9999\' AND interval=\'15m\' ORDER BY time DESC LIMIT 200', conn)
conn.close()

fe = FeatureEngineer()
for d in [df, df_train]:
    for c in ['open','high','low','close','volume','open_interest']:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    d.sort_values('timestamp', inplace=True)
    d.reset_index(drop=True, inplace=True)

df_feat = fe.generate_features(df)
df_train_feat = fe.generate_features(df_train)

print('\n--- Key feature comparison (au2606 inference vs au9999 training) ---')
for feat in ['rsi', 'macd', 'bb_position', 'volume_ratio_5', 'atr_ratio', 'ma_5']:
    if feat in df_feat.columns and feat in df_train_feat.columns:
        inf_val = df_feat[feat].dropna().iloc[-1] if len(df_feat[feat].dropna()) > 0 else None
        train_mean = df_train_feat[feat].mean()
        train_std = df_train_feat[feat].std()
        print(f'{feat}: inference={inf_val:.4f}, train_mean={train_mean:.4f}, train_std={train_std:.4f}')

# Make prediction
avail = [f for f in model_features if f in df_feat.columns]
latest = df_feat[avail].dropna().iloc[-1:]
if len(latest) > 0:
    pred = model.predict(latest)[0]
    print(f'\nPrediction: {pred:.6f}')
    print(f'abs(pred): {abs(pred):.6f}')
else:
    print('No valid row for prediction')
