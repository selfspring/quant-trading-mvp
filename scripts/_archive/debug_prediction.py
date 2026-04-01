"""检查模型对不同输入的预测值分布"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from quant.signal_generator.ml_predictor import MLPredictor
from quant.signal_generator.feature_engineer import FeatureEngineer

# 1. 用训练数据测试预测值分布
print("=== 用训练数据测试 ===")
df = pd.read_csv('E:/quant-trading-mvp/data/tq_au_30m_10000.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.rename(columns={'datetime': 'timestamp'})
df['open_interest'] = df['close_oi']
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_interest']]
df = df.sort_values('timestamp').reset_index(drop=True)

predictor = MLPredictor()

# 取不同时间段的 100 根 K 线测试
test_points = [500, 2000, 5000, 7000, 8000, 9000, 9500, 9900]
print(f"{'位置':<8} {'预测值':<12} {'置信度':<10} {'信号':<6}")
print("-" * 40)
for idx in test_points:
    chunk = df.iloc[idx-100:idx].copy().reset_index(drop=True)
    result = predictor.predict(chunk)
    print(f"{idx:<8} {result['prediction']:<12.6f} {result['confidence']:<10.4f} {result['signal']:<6}")

# 2. 用 AkShare 实时数据测试
print("\n=== 用 AkShare 实时数据测试 ===")
import akshare as ak
ak_df = ak.futures_zh_minute_sina(symbol='au2606', period="1")
ak_df = ak_df.tail(100).copy()
ak_df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'hold']
ak_df = ak_df.rename(columns={'hold': 'open_interest'})
ak_df = ak_df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_interest']]
for col in ['open', 'high', 'low', 'close', 'volume', 'open_interest']:
    ak_df[col] = pd.to_numeric(ak_df[col], errors='coerce')
ak_df = ak_df.sort_values('timestamp').reset_index(drop=True)

result = predictor.predict(ak_df)
print(f"AkShare: prediction={result['prediction']:.6f}, confidence={result['confidence']:.4f}, signal={result['signal']}")

# 3. 查看模型特征重要性
print("\n=== 模型特征重要性 Top 10 ===")
import lightgbm as lgb
model = lgb.Booster(model_file='models/lgbm_model.txt')
importance = model.feature_importance(importance_type='gain')
feature_names = model.feature_name()
pairs = sorted(zip(feature_names, importance), key=lambda x: -x[1])
for name, imp in pairs[:10]:
    print(f"  {name:<25} {imp:.2f}")

# 4. 查看模型结构
print(f"\n=== 模型结构 ===")
print(f"树的数量: {model.num_trees()}")
print(f"特征数量: {model.num_feature()}")
