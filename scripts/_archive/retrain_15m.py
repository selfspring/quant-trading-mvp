"""
用全量 au9999 15m 数据重训模型，优化参数
"""
import os, sys, time
import pandas as pd
import numpy as np
import psycopg2
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit

sys.path.insert(0, r'E:\quant-trading-mvp')

DB_PARAMS = dict(host='localhost', port=5432, dbname='quant_trading',
                 user='postgres', password='@Cmx1454697261')

def main():
    t0 = time.time()
    
    # 读数据
    print('Loading 15m data...')
    conn = psycopg2.connect(**DB_PARAMS)
    df = pd.read_sql(
        "SELECT time as timestamp, open, high, low, close, volume, open_interest "
        "FROM kline_data WHERE symbol='au9999' AND interval='15m' ORDER BY time",
        conn
    )
    conn.close()
    print(f'Loaded: {len(df):,} rows')
    
    for c in ['open','high','low','close','volume','open_interest']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['symbol'] = 'au9999'
    df['interval'] = '15m'
    
    # 特征工程
    from quant.signal_generator.feature_engineer import FeatureEngineer
    fe = FeatureEngineer()
    df_feat = fe.generate_features(df)
    print(f'After feature engineering: {df_feat.shape}')
    
    # 目标变量：4 根 15m K 线后的对数收益率（即 1 小时后）
    horizon = 4
    df_feat['target'] = np.log(
        df_feat['close'].shift(-horizon) / df_feat['close']
    )
    
    # 特征列
    drop_cols = {'timestamp','symbol','interval','open','high','low','close',
                 'volume','open_interest','target','datetime','time'}
    feature_cols = [c for c in df_feat.columns if c not in drop_cols]
    
    # 先丢弃高 NaN 列（>30%），再按行 dropna
    df_sub = df_feat[feature_cols + ['target']]
    nan_ratio = df_sub.isnull().mean()
    bad_cols = nan_ratio[nan_ratio > 0.3].index.tolist()
    if bad_cols:
        print(f'Dropping {len(bad_cols)} high-NaN cols: {bad_cols}')
        feature_cols = [c for c in feature_cols if c not in bad_cols]
    
    df_clean = df_feat[feature_cols + ['target']].dropna().copy()
    print(f'Clean rows: {len(df_clean):,}, features: {len(feature_cols)}')
    
    X = df_clean[feature_cols].astype(float)
    y = df_clean['target'].astype(float)
    
    print(f'Target stats: mean={y.mean():.6f}, std={y.std():.6f}')
    print(f'Direction balance: {(y>0).mean():.2%} positive')
    
    # 80/20 时序分割
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    print(f'Train: {len(X_train):,}, Test: {len(X_test):,}')
    
    # 训练
    print('Training...')
    train_data = lgb.Dataset(X_train, label=y_train)
    valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
    
    params = {
        'objective': 'regression',
        'metric': 'mse',
        'boosting_type': 'gbdt',
        'num_leaves': 63,
        'learning_rate': 0.01,
        'feature_fraction': 0.7,
        'bagging_fraction': 0.7,
        'bagging_freq': 5,
        'min_child_samples': 50,
        'lambda_l1': 0.1,
        'lambda_l2': 0.1,
        'verbose': -1,
        'n_jobs': -1
    }
    
    callbacks = [
        lgb.log_evaluation(200),
        lgb.early_stopping(100, verbose=True)
    ]
    
    model = lgb.train(
        params, train_data,
        num_boost_round=2000,
        valid_sets=[valid_data],
        callbacks=callbacks
    )
    
    # 评估
    y_pred = model.predict(X_test)
    mse = float(np.mean((y_test - y_pred)**2))
    rmse = float(np.sqrt(mse))
    corr = float(np.corrcoef(y_test, y_pred)[0,1])
    dir_acc = float(np.mean(np.sign(y_test) == np.sign(y_pred)))
    
    print(f'\n=== Model Performance ===')
    print(f'MSE:  {mse:.6f}')
    print(f'RMSE: {rmse:.6f}')
    print(f'Corr: {corr:.4f}')
    print(f'DirAcc: {dir_acc:.4%}')
    print(f'Features: {len(model.feature_name())}')
    print(f'Best iteration: {model.best_iteration}')
    
    # Top 10 features
    importance = sorted(zip(model.feature_name(), model.feature_importance()),
                        key=lambda x: -x[1])
    print('\nTop 10 important features:')
    for fname, imp in importance[:10]:
        print(f'  {fname}: {imp}')
    
    # 备份旧模型，保存新模型
    import shutil
    model_path = r'models\lgbm_model.txt'
    if os.path.exists(model_path):
        shutil.copy2(model_path, model_path + '.bak')
    model.save_model(model_path)
    print(f'\nModel saved: {model_path}')
    print(f'Total time: {time.time()-t0:.0f}s')


if __name__ == '__main__':
    main()
