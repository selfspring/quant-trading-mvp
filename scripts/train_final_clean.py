"""重新训练模型，排除 open_oi 和 close_oi"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_squared_error
from quant.signal_generator.feature_engineer import FeatureEngineer

print("=== 加载数据 ===")
df = pd.read_csv('E:/quant-trading-mvp/data/tq_au_30m_10000.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.rename(columns={'datetime': 'timestamp'})

# 只保留实时数据也能拿到的字段
df['open_interest'] = df['close_oi']
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_interest']]
df = df.sort_values('timestamp').reset_index(drop=True)
print(f"数据: {len(df)} 行")

print("\n=== 特征工程 ===")
fe = FeatureEngineer()
X, y = fe.prepare_training_data(df)
print(f"特征: {X.shape[1]} 个")
print(f"特征列: {list(X.columns)}")

# 划分
split_idx = int(len(X) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]
print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")

# 使用 regularized 参数（之前调参最佳）
print("\n=== 训练模型 ===")
params = {
    'learning_rate': 0.05,
    'num_leaves': 31,
    'max_depth': 6,
    'min_data_in_leaf': 20,
    'lambda_l1': 0.1,
    'lambda_l2': 0.1,
    'objective': 'regression',
    'metric': 'rmse',
    'random_state': 42,
    'verbose': -1
}

model = lgb.LGBMRegressor(**params)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50, verbose=False),
        lgb.log_evaluation(period=0)
    ]
)

# 评估
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
direction_acc = (np.sign(y_pred) == np.sign(y_test)).sum() / len(y_test)
correlation = np.corrcoef(y_pred, y_test)[0, 1]

print(f"\n=== 结果 ===")
print(f"特征数: {X.shape[1]}")
print(f"RMSE: {rmse:.6f} ({rmse*100:.2f}%)")
print(f"方向准确率: {direction_acc*100:.2f}%")
print(f"相关系数: {correlation:.4f}")
print(f"迭代次数: {model.best_iteration_}")

# 保存
model.booster_.save_model('E:/quant-trading-mvp/models/lgbm_model.txt')
print(f"\n[OK] 模型已保存 (特征数: {X.shape[1]})")

# 验证特征列表
saved_model = lgb.Booster(model_file='E:/quant-trading-mvp/models/lgbm_model.txt')
print(f"模型特征: {saved_model.feature_name()}")
