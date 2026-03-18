"""深度调参：让模型学到更多树"""
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
df['open_interest'] = df['close_oi']
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_interest']]
df = df.sort_values('timestamp').reset_index(drop=True)

fe = FeatureEngineer()
X, y = fe.prepare_training_data(df)
split_idx = int(len(X) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]
print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}, 特征: {X.shape[1]}")

param_sets = [
    {
        'name': 'low_lr_deep',
        'params': {
            'learning_rate': 0.005,
            'num_leaves': 63,
            'max_depth': 8,
            'min_data_in_leaf': 50,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'lambda_l1': 0.01,
            'lambda_l2': 0.01,
            'n_estimators': 1000,
            'objective': 'regression',
            'metric': 'rmse',
            'random_state': 42,
            'verbose': -1
        }
    },
    {
        'name': 'very_low_lr',
        'params': {
            'learning_rate': 0.001,
            'num_leaves': 31,
            'max_depth': 6,
            'min_data_in_leaf': 30,
            'feature_fraction': 0.7,
            'bagging_fraction': 0.7,
            'bagging_freq': 5,
            'lambda_l1': 0.001,
            'lambda_l2': 0.001,
            'n_estimators': 2000,
            'objective': 'regression',
            'metric': 'rmse',
            'random_state': 42,
            'verbose': -1
        }
    },
    {
        'name': 'huber_loss',
        'params': {
            'learning_rate': 0.005,
            'num_leaves': 63,
            'max_depth': 8,
            'min_data_in_leaf': 50,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'lambda_l1': 0.01,
            'lambda_l2': 0.01,
            'n_estimators': 1000,
            'objective': 'huber',
            'alpha': 0.5,
            'metric': 'rmse',
            'random_state': 42,
            'verbose': -1
        }
    },
    {
        'name': 'no_early_stop',
        'params': {
            'learning_rate': 0.01,
            'num_leaves': 31,
            'max_depth': 6,
            'min_data_in_leaf': 30,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'lambda_l1': 0.05,
            'lambda_l2': 0.05,
            'n_estimators': 200,
            'objective': 'regression',
            'metric': 'rmse',
            'random_state': 42,
            'verbose': -1
        }
    }
]

results = []

for ps in param_sets:
    name = ps['name']
    params = ps['params']
    use_early_stop = name != 'no_early_stop'
    
    print(f"\n=== {name} ===")
    model = lgb.LGBMRegressor(**params)
    
    fit_params = {}
    if use_early_stop:
        fit_params['eval_set'] = [(X_test, y_test)]
        fit_params['callbacks'] = [
            lgb.early_stopping(stopping_rounds=100, verbose=False),
            lgb.log_evaluation(period=0)
        ]
    
    model.fit(X_train, y_train, **fit_params)
    
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    direction_acc = (np.sign(y_pred) == np.sign(y_test)).sum() / len(y_test)
    correlation = np.corrcoef(y_pred, y_test)[0, 1]
    
    # 预测值分布
    pred_std = np.std(y_pred)
    pred_range = np.max(y_pred) - np.min(y_pred)
    n_trees = model.best_iteration_ if use_early_stop else params['n_estimators']
    
    results.append({
        'name': name, 'rmse': rmse, 'direction_acc': direction_acc,
        'correlation': correlation, 'trees': n_trees,
        'pred_std': pred_std, 'pred_range': pred_range, 'model': model
    })
    
    print(f"  树数量: {n_trees}")
    print(f"  RMSE: {rmse:.6f} ({rmse*100:.2f}%)")
    print(f"  方向准确率: {direction_acc*100:.2f}%")
    print(f"  相关系数: {correlation:.4f}")
    print(f"  预测值标准差: {pred_std:.6f}")
    print(f"  预测值范围: {pred_range:.6f}")

# 对比
print("\n=== 结果对比 ===")
print(f"{'参数组':<16} {'树':<6} {'RMSE':<10} {'方向':<8} {'相关':<8} {'预测std':<10} {'预测range':<10}")
print("-" * 80)
for r in results:
    print(f"{r['name']:<16} {r['trees']:<6} {r['rmse']:<10.6f} {r['direction_acc']*100:<8.2f} {r['correlation']:<8.4f} {r['pred_std']:<10.6f} {r['pred_range']:<10.6f}")

# 选最佳
best = max(results, key=lambda x: x['direction_acc'] * 0.4 + max(x['correlation'], 0) * 0.3 + min(x['pred_std'] * 100, 0.3) * 0.3)
print(f"\n最佳: {best['name']}")
best['model'].booster_.save_model('E:/quant-trading-mvp/models/lgbm_model.txt')
print("[OK] 模型已保存")
