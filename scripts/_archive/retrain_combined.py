"""
用 au_continuous 1m 数据聚合 15m，再训练模型
训练域与推理域一致（都是近1年主力连续合约数据）
"""
import os, sys, time, shutil
import pandas as pd
import numpy as np
import psycopg2
import lightgbm as lgb

sys.path.insert(0, r'E:\quant-trading-mvp')

DB_PARAMS = dict(host='localhost', port=5432, dbname='quant_trading',
                 user='postgres', password='@Cmx1454697261')

def resample_to_15m(df):
    """1m -> 15m 聚合"""
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.set_index('timestamp').sort_index()
    df_15m = df.resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'open_interest': 'last'
    }).dropna()
    df_15m = df_15m.reset_index()
    df_15m.columns = ['timestamp','open','high','low','close','volume','open_interest']
    return df_15m

def main():
    t0 = time.time()

    # 1. 读 au_continuous 1m
    print('Loading au_continuous 1m...')
    conn = psycopg2.connect(**DB_PARAMS)
    df1m = pd.read_sql(
        "SELECT time as timestamp, open, high, low, close, volume, open_interest "
        "FROM kline_data WHERE symbol='au_continuous' AND interval='1m' ORDER BY time",
        conn
    )
    # 也读 au2606 1m 补充最近数据
    df2606 = pd.read_sql(
        "SELECT time as timestamp, open, high, low, close, volume, open_interest "
        "FROM kline_data WHERE symbol='au2606' AND interval='1m' ORDER BY time",
        conn
    )
    conn.close()

    for c in ['open','high','low','close','volume','open_interest']:
        df1m[c] = pd.to_numeric(df1m[c], errors='coerce')
        df2606[c] = pd.to_numeric(df2606[c], errors='coerce')

    print(f'au_continuous 1m: {len(df1m):,} rows')
    print(f'au2606 1m: {len(df2606):,} rows')

    # 合并，去重，按时间排序
    df_all = pd.concat([df1m, df2606], ignore_index=True)
    df_all['timestamp'] = pd.to_datetime(df_all['timestamp'], utc=True)
    df_all = df_all.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    print(f'Combined 1m: {len(df_all):,} rows | {df_all["timestamp"].min()} ~ {df_all["timestamp"].max()}')

    # 2. 聚合成 15m
    print('Resampling to 15m...')
    df15m = resample_to_15m(df_all)
    df15m['symbol'] = 'au_combined'
    df15m['interval'] = '15m'
    print(f'15m bars: {len(df15m):,}')

    # 3. 特征工程
    from quant.signal_generator.feature_engineer import FeatureEngineer
    fe = FeatureEngineer()
    df_feat = fe.generate_features(df15m)
    print(f'After feature engineering: {df_feat.shape}')

    # 4. 目标变量：4根15m后（1小时）
    horizon = 4
    df_feat['target'] = np.log(
        df_feat['close'].shift(-horizon) / df_feat['close']
    )

    # 5. 特征列，丢弃高 NaN 列
    drop_cols = {'timestamp','symbol','interval','open','high','low','close',
                 'volume','open_interest','target','datetime','time'}
    feature_cols = [c for c in df_feat.columns if c not in drop_cols]

    nan_ratio = df_feat[feature_cols + ['target']].isnull().mean()
    bad_cols = nan_ratio[nan_ratio > 0.3].index.tolist()
    if bad_cols:
        print(f'Dropping {len(bad_cols)} high-NaN cols: {bad_cols}')
        feature_cols = [c for c in feature_cols if c not in bad_cols]

    df_clean = df_feat[feature_cols + ['target']].dropna().copy()
    print(f'Clean rows: {len(df_clean):,}, features: {len(feature_cols)}')

    if len(df_clean) < 100:
        print('ERROR: Not enough clean rows!')
        return

    X = df_clean[feature_cols].astype(float)
    y = df_clean['target'].astype(float)

    print(f'Target: mean={y.mean():.6f}, std={y.std():.6f}')
    print(f'Direction balance: {(y>0).mean():.2%} positive')

    # 6. 训练/测试分割
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    print(f'Train: {len(X_train):,}, Test: {len(X_test):,}')

    # 7. 训练
    print('Training...')
    train_data = lgb.Dataset(X_train, label=y_train)
    valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    params = {
        'objective': 'regression',
        'metric': 'mse',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'min_child_samples': 20,
        'lambda_l1': 0.05,
        'lambda_l2': 0.05,
        'verbose': -1,
        'n_jobs': -1
    }

    callbacks = [
        lgb.log_evaluation(100),
        lgb.early_stopping(100, verbose=True)
    ]

    model = lgb.train(
        params, train_data,
        num_boost_round=1000,
        valid_sets=[valid_data],
        callbacks=callbacks
    )

    # 8. 评估
    y_pred = model.predict(X_test)
    mse = float(np.mean((y_test - y_pred)**2))
    corr = float(np.corrcoef(y_test, y_pred)[0,1])
    dir_acc = float(np.mean(np.sign(y_test) == np.sign(y_pred)))

    print(f'\n=== Model Performance ===')
    print(f'MSE:  {mse:.6f}')
    print(f'Corr: {corr:.4f}')
    print(f'DirAcc: {dir_acc:.4%}')
    print(f'Best iteration: {model.best_iteration}')
    print(f'Features: {len(model.feature_name())}')

    # 预测值分布
    print(f'Pred std: {y_pred.std():.6f}, mean: {y_pred.mean():.6f}')
    print(f'Pred >0.0015: {(y_pred > 0.0015).mean():.2%}')
    print(f'Pred <-0.0015: {(y_pred < -0.0015).mean():.2%}')

    print('\nTop 10 features:')
    importance = sorted(zip(model.feature_name(), model.feature_importance()), key=lambda x: -x[1])
    for fname, imp in importance[:10]:
        print(f'  {fname}: {imp}')

    # 9. 保存
    model_path = r'models\lgbm_model.txt'
    if os.path.exists(model_path):
        shutil.copy2(model_path, model_path + '.bak')
    model.save_model(model_path)
    print(f'\nModel saved: {model_path}')
    print(f'Total: {time.time()-t0:.0f}s')

if __name__ == '__main__':
    main()
