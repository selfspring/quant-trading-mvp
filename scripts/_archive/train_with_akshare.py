"""用 AkShare 真实数据重新训练 ML 模型"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from quant.signal_generator.feature_engineer import FeatureEngineer
from quant.signal_generator.model_trainer import ModelTrainer

print("=== 加载真实数据 ===")
df = pd.read_csv('E:/quant-trading-mvp/data/au_main_daily.csv')
print(f"原始数据: {len(df)} 行")
print(f"列名: {list(df.columns)}")

# 转换为标准格式
df_clean = df.rename(columns={'date': 'timestamp'})
df_clean = df_clean[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
print(f"清洗后: {len(df_clean)} 行")
print(df_clean.head(3))

print("\n=== 特征工程 ===")
fe = FeatureEngineer()
X, y = fe.prepare_training_data(df_clean)
print(f"特征矩阵: {X.shape}")
print(f"标签: {y.shape}")
print(f"特征列: {list(X.columns)}")

print("\n=== 划分训练集和测试集 ===")
split_idx = int(len(X) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]
print(f"训练集: {len(X_train)} 行")
print(f"测试集: {len(X_test)} 行")

print("\n=== 训练模型 ===")
trainer = ModelTrainer()
model, metrics = trainer.train(X_train, y_train, X_test, y_test)

print("\n=== 训练结果 ===")
print(f"测试集 MSE: {metrics['mse']:.6f}")
print(f"测试集 RMSE: {metrics['rmse']:.6f}")

print("\n=== 预测值分布 ===")
y_pred = model.predict(X_test)
print(f"最小值: {y_pred.min():.6f}")
print(f"最大值: {y_pred.max():.6f}")
print(f"均值: {y_pred.mean():.6f}")
print(f"标准差: {y_pred.std():.6f}")

print("\n=== 保存模型 ===")
trainer.save_model()
print("模型已保存: models/lgbm_model.txt")
