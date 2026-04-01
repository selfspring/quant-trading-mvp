"""超参数调优并重新训练"""
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
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_oi', 'close_oi']]
df = df.sort_values('timestamp').reset_index(drop=True)

# 添加 open_interest 列（取 close_oi）
df['open_interest'] = df['close_oi']

print(f"数据: {len(df)} 行")

print("\n=== 特征工程 ===")
fe = FeatureEngineer()
X, y = fe.prepare_training_data(df)
print(f"特征: {X.shape[1]} 个")

# 划分数据集
split_idx = int(len(X) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")

# 测试多组超参数
param_sets = [
    {
        'name': 'baseline',
        'params': {
            'learning_rate': 0.05,
            'num_leaves': 31,
            'max_depth': 6,
            'min_data_in_leaf': 20,
            'objective': 'regression',
            'metric': 'rmse',
            'random_state': 42,
            'verbose': -1
        }
    },
    {
        'name': 'deeper',
        'params': {
            'learning_rate': 0.03,
            'num_leaves': 63,
            'max_depth': 8,
            'min_data_in_leaf': 15,
            'objective': 'regression',
            'metric': 'rmse',
            'random_state': 42,
            'verbose': -1
        }
    },
    {
        'name': 'regularized',
        'params': {
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
    },
    {
        'name': 'boosted',
        'params': {
            'learning_rate': 0.01,
            'num_leaves': 31,
            'max_depth': 6,
            'min_data_in_leaf': 20,
            'n_estimators': 500,
            'objective': 'regression',
            'metric': 'rmse',
            'random_state': 42,
            'verbose': -1
        }
    }
]

results = []

for param_set in param_sets:
    name = param_set['name']
    params = param_set['params']
    
    print(f"\n=== 测试参数组: {name} ===")
    
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
    
    # 方向准确率
    pred_direction = np.sign(y_pred)
    actual_direction = np.sign(y_test)
    direction_acc = (pred_direction == actual_direction).sum() / len(y_test)
    
    # 相关系数
    correlation = np.corrcoef(y_pred, y_test)[0, 1]
    
    results.append({
        'name': name,
        'rmse': rmse,
        'direction_acc': direction_acc,
        'correlation': correlation,
        'iterations': model.best_iteration_,
        'model': model
    })
    
    print(f"  RMSE: {rmse:.6f} ({rmse*100:.2f}%)")
    print(f"  方向准确率: {direction_acc*100:.2f}%")
    print(f"  相关系数: {correlation:.4f}")
    print(f"  迭代次数: {model.best_iteration_}")

# 选择最佳模型
print("\n=== 结果对比 ===")
print(f"{'参数组':<15} {'RMSE':<10} {'方向准确率':<12} {'相关系数':<10} {'迭代次数':<10}")
print("-" * 70)
for r in results:
    print(f"{r['name']:<15} {r['rmse']:<10.6f} {r['direction_acc']*100:<12.2f} {r['correlation']:<10.4f} {r['iterations']:<10}")

# 选择综合得分最高的
best = max(results, key=lambda x: x['direction_acc'] * 0.5 + (x['correlation'] if x['correlation'] > 0 else 0) * 0.5)
print(f"\n最佳参数组: {best['name']}")

# 保存最佳模型
best['model'].booster_.save_model('E:/quant-trading-mvp/models/lgbm_model.txt')
print(f"[OK] 已保存最佳模型")
