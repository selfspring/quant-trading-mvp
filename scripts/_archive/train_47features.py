# -*- coding: utf-8 -*-
"""
用当前 FeatureEngineer 的47个特征重新训练 LightGBM 模型
"""
import sys, os
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from scipy.stats import pearsonr
import psycopg2
from quant.signal_generator.feature_engineer import FeatureEngineer

print('=== 重新训练 47特征 LightGBM 模型 ===')

# 1. 加载数据
conn = psycopg2.connect(host='localhost', port=5432, dbname='quant_trading',
                         user='postgres', password='@Cmx1454697261')
cursor = conn.cursor()
cursor.execute("""
    SELECT time as timestamp, open, high, low, close, volume,
           COALESCE(open_interest, 0) as open_interest
    FROM kline_data
    WHERE symbol IN ('au_main', 'au2606') AND interval = '30m'
    ORDER BY time ASC
""")
rows = cursor.fetchall()
cols = [d[0] for d in cursor.description]
df = pd.DataFrame(rows, columns=cols)
# psycopg2 返回 Decimal 类型，转换为 float
for col in ['open', 'high', 'low', 'close', 'volume', 'open_interest']:
    df[col] = df[col].astype(float)
conn.close()
print(f'加载数据: {len(df)} 根K线')

# 2. 生成特征
fe = FeatureEngineer()
df_feat = fe.generate_features(df)
print(f'特征数: {len(df_feat.columns)}')

# 3. 剔除非特征列（与 ml_predictor.py 保持一致：只 drop timestamp）
meta_cols = ['timestamp']
feature_cols = [c for c in df_feat.columns if c not in meta_cols]
# 过滤掉非数值列
import pandas as pd
df_feat_tmp = df_feat[feature_cols].select_dtypes(include='number')
feature_cols = list(df_feat_tmp.columns)
print(f'纯特征数: {len(feature_cols)}')

# 4. 目标变量：未来2根K线（60分钟）对数收益率
df_feat['target'] = np.log(df_feat['close'].shift(-2) / df_feat['close'])
df_feat = df_feat.dropna(subset=feature_cols + ['target'])

X = df_feat[feature_cols].values
y = df_feat['target'].values
print(f'样本数: {len(X)}')

# 5. 划分训练/测试集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, shuffle=False)
print(f'训练: {len(X_train)}, 测试: {len(X_test)}')

# 6. 训练
train_data = lgb.Dataset(X_train, label=y_train, feature_name=feature_cols)
val_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

params = {
    'objective': 'regression',
    'metric': 'mse',
    'n_estimators': 500,
    'learning_rate': 0.01,
    'num_leaves': 31,
    'min_child_samples': 50,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'reg_alpha': 0.1,
    'reg_lambda': 0.1,
    'verbose': -1,
}

callbacks = [
    lgb.early_stopping(stopping_rounds=50, verbose=True),
    lgb.log_evaluation(period=50),
]

model = lgb.train(
    params,
    train_data,
    valid_sets=[val_data],
    num_boost_round=500,
    callbacks=callbacks,
)

# 7. 评估
preds = model.predict(X_test)
mse = mean_squared_error(y_test, preds)
rmse = np.sqrt(mse)
corr, _ = pearsonr(y_test, preds)
direction_acc = np.mean(np.sign(preds) == np.sign(y_test))

print(f'\n=== 评估结果 ===')
print(f'MSE:  {mse:.6f}')
print(f'RMSE: {rmse:.6f}')
print(f'相关系数: {corr:.4f}')
print(f'方向准确率: {direction_acc:.4f}')
print(f'预测分布: mean={preds.mean():.6f}, std={preds.std():.6f}')

# 信号统计
threshold = 0.003
buys = np.sum(preds > threshold)
sells = np.sum(preds < -threshold)
print(f'信号统计 (阈值={threshold}): buy={buys}, sell={sells}, neutral={len(preds)-buys-sells}')

# 8. 保存
model_path = 'models/lgbm_model.txt'
model.save_model(model_path)
print(f'\n模型已保存: {model_path}')
print(f'特征数: {model.num_feature()}')
print(f'迭代数: {model.best_iteration}')
