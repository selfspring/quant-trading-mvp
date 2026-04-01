"""用 8000 根真实 30 分钟线 + 增强特征训练模型"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from quant.signal_generator.feature_engineer import FeatureEngineer
from quant.signal_generator.model_trainer import ModelTrainer

print("=== 加载真实 30 分钟线数据 ===")
df = pd.read_csv('E:/quant-trading-mvp/data/tq_au_30m_8000.csv')
print(f"原始数据: {len(df)} 行")

# 转换时间戳
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.rename(columns={'datetime': 'timestamp'})
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"清洗后: {len(df)} 行")
print(f"时间范围: {df.iloc[0]['timestamp']} ~ {df.iloc[-1]['timestamp']}")

print("\n=== 特征工程（使用现有 FeatureEngineer）===")
fe = FeatureEngineer()
X, y = fe.prepare_training_data(df)
print(f"特征矩阵: {X.shape}")
print(f"标签: {y.shape}")
print(f"特征数量: {X.shape[1]}")

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
print(f"测试集 RMSE: {metrics['rmse']:.6f} ({metrics['rmse']*100:.2f}%)")

print("\n=== 预测值分布 ===")
y_pred = model.predict(X_test)
print(f"最小值: {y_pred.min():.6f} ({y_pred.min()*100:.2f}%)")
print(f"最大值: {y_pred.max():.6f} ({y_pred.max()*100:.2f}%)")
print(f"均值: {y_pred.mean():.6f} ({y_pred.mean()*100:.2f}%)")
print(f"标准差: {y_pred.std():.6f} ({y_pred.std()*100:.2f}%)")

print("\n=== 方向准确率 ===")
pred_direction = np.sign(y_pred)
actual_direction = np.sign(y_test)
direction_correct = (pred_direction == actual_direction).sum()
direction_accuracy = direction_correct / len(y_test)
print(f"方向准确率: {direction_accuracy*100:.2f}% ({direction_correct}/{len(y_test)})")

print("\n=== 相关性 ===")
correlation = np.corrcoef(y_pred, y_test)[0, 1]
print(f"预测与实际的相关系数: {correlation:.4f}")

print("\n=== 保存模型 ===")
trainer.save_model()
print("模型已保存: models/lgbm_model.txt")

print("\n=== 模型评级 ===")
score = 0
if metrics['rmse'] < 0.03:
    score += 2
    print("[OK] RMSE < 3%")
elif metrics['rmse'] < 0.05:
    score += 1
    print("[OK] RMSE < 5%")
else:
    print("[WARN] RMSE >= 5%")

if direction_accuracy > 0.55:
    score += 2
    print("[OK] 方向准确率 > 55%")
elif direction_accuracy > 0.50:
    score += 1
    print("[OK] 方向准确率 > 50%")
else:
    print("[WARN] 方向准确率 <= 50%")

if correlation > 0.2:
    score += 2
    print("[OK] 相关系数 > 0.2")
elif correlation > 0.1:
    score += 1
    print("[OK] 相关系数 > 0.1")
else:
    print("[WARN] 相关系数 <= 0.1")

print(f"\n总分: {score}/6")
if score >= 5:
    print("模型质量: 优秀")
elif score >= 3:
    print("模型质量: 良好")
else:
    print("模型质量: 需改进")
