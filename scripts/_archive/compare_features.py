"""对比训练特征和预测特征"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import lightgbm as lgb
from quant.signal_generator.feature_engineer import FeatureEngineer

# 1. 模型期望的特征
model = lgb.Booster(model_file='models/lgbm_model.txt')
train_features = model.feature_name()
print(f"模型训练特征 ({len(train_features)}):")
for i, f in enumerate(train_features):
    print(f"  {i+1}. {f}")

# 2. AkShare 数据生成的特征
import akshare as ak
df = ak.futures_zh_minute_sina(symbol='au2606', period="1")
df = df.tail(100).copy()
df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'hold']
df = df.rename(columns={'hold': 'open_interest'})
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_interest']]
for col in ['open', 'high', 'low', 'close', 'volume', 'open_interest']:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.sort_values('timestamp').reset_index(drop=True)

fe = FeatureEngineer()
df_feat = fe.generate_features(df)
df_feat = df_feat.dropna()
if 'timestamp' in df_feat.columns:
    df_feat = df_feat.drop(columns=['timestamp'])

predict_features = list(df_feat.columns)
print(f"\n预测时特征 ({len(predict_features)}):")
for i, f in enumerate(predict_features):
    print(f"  {i+1}. {f}")

# 3. 差异
missing = set(train_features) - set(predict_features)
extra = set(predict_features) - set(train_features)
print(f"\n缺少的特征: {missing}")
print(f"多余的特征: {extra}")
