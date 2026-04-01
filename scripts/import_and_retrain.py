"""
黄金期货历史数据导入 + 聚合 + 模型重训
Step 1: 导入 1m CSV → kline_data
Step 2: 聚合为 15m K 线 → kline_data  
Step 3: 用 15m 数据重训 LightGBM
"""
import os, sys, glob, time
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

sys.path.insert(0, r'E:\quant-trading-mvp')

DB_PARAMS = dict(host='localhost', port=5432, dbname='quant_trading', 
                 user='postgres', password='@Cmx1454697261')

# ============ Step 1: 导入 1m CSV ============
def import_1m_data():
    print("=" * 60)
    print("Step 1: 导入 1m K 线数据")
    print("=" * 60)
    
    files = sorted(glob.glob(r'data\raw_gold\**\AU9999*.csv', recursive=True))
    print(f"Found {len(files)} CSV files")
    
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    total_inserted = 0
    total_skipped = 0
    
    for fpath in files:
        fname = os.path.basename(fpath)
        df = pd.read_csv(fpath)
        
        # 重命名时间列
        df.rename(columns={'Unnamed: 0': 'time'}, inplace=True)
        
        # 只保留需要的列
        cols = ['time', 'open', 'high', 'low', 'close', 'volume', 'open_interest']
        for c in cols:
            if c not in df.columns:
                print(f"  WARNING: {fname} missing column {c}")
                continue
        
        df = df[cols].copy()
        
        # 去掉 OHLCV 全为 NaN 的行
        ohlcv = ['open', 'high', 'low', 'close', 'volume']
        df = df.dropna(subset=ohlcv, how='all')
        
        # 去掉 open/close 为 NaN 的行
        df = df.dropna(subset=['open', 'close'])
        
        if df.empty:
            print(f"  {fname}: 0 valid rows, skipped")
            continue
        
        # 填充 open_interest 的 NaN
        df['open_interest'] = df['open_interest'].fillna(0)
        df['volume'] = df['volume'].fillna(0)
        
        # 转时间戳（加北京时区）
        df['time'] = pd.to_datetime(df['time'])
        df['time'] = df['time'].dt.tz_localize('Asia/Shanghai')
        
        # 批量插入
        batch_size = 5000
        file_inserted = 0
        
        for start in range(0, len(df), batch_size):
            batch = df.iloc[start:start + batch_size]
            values = [
                (row['time'], 'au9999', '1m', 
                 float(row['open']), float(row['high']), float(row['low']), 
                 float(row['close']), float(row['volume']), float(row['open_interest']))
                for _, row in batch.iterrows()
            ]
            
            try:
                execute_values(cursor, """
                    INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
                    VALUES %s
                    ON CONFLICT DO NOTHING
                """, values)
                conn.commit()
                file_inserted += len(values)
            except Exception as e:
                conn.rollback()
                print(f"  ERROR in {fname} batch {start}: {e}")
        
        total_inserted += file_inserted
        print(f"  {fname}: {len(df)} rows -> {file_inserted} inserted")
    
    # 验证
    cursor.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au9999' AND interval='1m'")
    db_count = cursor.fetchone()[0]
    print(f"\nTotal inserted: {total_inserted}")
    print(f"DB total (au9999 1m): {db_count}")
    
    conn.close()
    return db_count


# ============ Step 2: 聚合 15m K 线 ============
def aggregate_15m():
    print("\n" + "=" * 60)
    print("Step 2: 聚合 15m K 线")
    print("=" * 60)
    
    conn = psycopg2.connect(**DB_PARAMS)
    
    # 读取所有 1m 数据
    print("Reading 1m data from DB...")
    df = pd.read_sql("""
        SELECT time, open, high, low, close, volume, open_interest 
        FROM kline_data 
        WHERE symbol='au9999' AND interval='1m' 
        ORDER BY time
    """, conn)
    
    print(f"Total 1m rows: {len(df)}")
    
    df['time'] = pd.to_datetime(df['time'], utc=True).dt.tz_convert('Asia/Shanghai')
    df = df.set_index('time')
    
    # 转 float
    for col in ['open', 'high', 'low', 'close', 'volume', 'open_interest']:
        df[col] = df[col].astype(float)
    
    # 按 15 分钟聚合（用 label='left' 保持标准格式）
    print("Aggregating to 15m...")
    df_15m = df.resample('15min', label='left', closed='left').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'open_interest': 'last'
    }).dropna(subset=['open', 'close'])
    
    # 过滤非交易时段（volume=0 的大概率是非交易时段）
    df_15m = df_15m[df_15m['volume'] > 0]
    
    print(f"15m rows after aggregation: {len(df_15m)}")
    
    # 写入数据库
    cursor = conn.cursor()
    batch_size = 5000
    total = 0
    
    df_15m = df_15m.reset_index()
    
    for start in range(0, len(df_15m), batch_size):
        batch = df_15m.iloc[start:start + batch_size]
        values = [
            (row['time'], 'au9999', '15m',
             float(row['open']), float(row['high']), float(row['low']),
             float(row['close']), float(row['volume']), float(row['open_interest']))
            for _, row in batch.iterrows()
        ]
        
        try:
            execute_values(cursor, """
                INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
                VALUES %s
                ON CONFLICT DO NOTHING
            """, values)
            conn.commit()
            total += len(values)
        except Exception as e:
            conn.rollback()
            print(f"  ERROR batch {start}: {e}")
    
    # 验证
    cursor.execute("SELECT COUNT(*) FROM kline_data WHERE symbol='au9999' AND interval='15m'")
    db_count = cursor.fetchone()[0]
    print(f"Inserted: {total}, DB total (au9999 15m): {db_count}")
    
    conn.close()
    return db_count


# ============ Step 3: 重训模型 ============
def retrain_model():
    print("\n" + "=" * 60)
    print("Step 3: 重训 LightGBM 模型")
    print("=" * 60)
    
    import lightgbm as lgb
    from quant.signal_generator.feature_engineer import FeatureEngineer
    
    # 备份旧模型
    import shutil
    model_path = r'models\lgbm_model.txt'
    if os.path.exists(model_path):
        shutil.copy2(model_path, model_path + '.bak')
        print("Old model backed up")
    
    # 读取 15m 数据
    conn = psycopg2.connect(**DB_PARAMS)
    print("Reading 15m data...")
    df = pd.read_sql("""
        SELECT time as timestamp, 'au9999' as symbol, '15m' as interval,
               open, high, low, close, volume, open_interest 
        FROM kline_data 
        WHERE symbol='au9999' AND interval='15m' 
        ORDER BY time
    """, conn)
    conn.close()
    
    print(f"Total 15m rows: {len(df)}")
    
    # 转 float
    for col in ['open', 'high', 'low', 'close', 'volume', 'open_interest']:
        df[col] = df[col].astype(float)
    
    # 生成特征
    print("Generating features...")
    fe = FeatureEngineer()
    df_features = fe.generate_features(df)
    print(f"Features generated: {len(df_features)} rows, {len(df_features.columns)} columns")
    
    # 准备训练数据
    # 目标变量：60 根 K 线后的对数收益率
    horizon = 60
    df_features['target'] = np.log(df_features['close'].shift(-horizon) / df_features['close'])
    
    # 移除非特征列
    drop_cols = ['timestamp', 'symbol', 'interval', 'open', 'high', 'low', 'close', 
                 'volume', 'open_interest', 'target', 'datetime']
    feature_cols = [c for c in df_features.columns if c not in drop_cols]
    
    # 移除包含目标的行（最后 horizon 行）和包含 NaN 的行
    df_clean = df_features.dropna(subset=['target'] + feature_cols)
    print(f"Clean rows: {len(df_clean)}")
    
    if len(df_clean) < 1000:
        print("ERROR: Not enough clean data for training!")
        return
    
    X = df_clean[feature_cols].astype(float)
    y = df_clean['target'].astype(float)
    
    # 80/20 split (时间序列，不 shuffle)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")
    print(f"Feature count: {len(feature_cols)}")
    
    # 训练
    print("Training LightGBM...")
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
        'lambda_l1': 0.1,
        'lambda_l2': 0.1,
        'verbose': -1
    }
    
    callbacks = [lgb.log_evaluation(100), lgb.early_stopping(50)]
    model = lgb.train(
        params, train_data, 
        num_boost_round=1000,
        valid_sets=[valid_data],
        callbacks=callbacks
    )
    
    # 保存
    model.save_model(model_path)
    print(f"Model saved to {model_path}")
    
    # 评估
    y_pred = model.predict(X_test)
    mse = np.mean((y_test - y_pred) ** 2)
    rmse = np.sqrt(mse)
    corr = np.corrcoef(y_test, y_pred)[0, 1]
    
    # 方向准确率
    direction_correct = np.mean(np.sign(y_test) == np.sign(y_pred))
    
    print(f"\n--- Model Performance ---")
    print(f"MSE:  {mse:.6f}")
    print(f"RMSE: {rmse:.6f}")
    print(f"Correlation: {corr:.4f}")
    print(f"Direction Accuracy: {direction_correct:.4%}")
    print(f"Feature count: {len(model.feature_name())}")
    
    # Top 10 important features
    importance = sorted(zip(model.feature_name(), model.feature_importance()), 
                        key=lambda x: -x[1])
    print(f"\nTop 10 features:")
    for fname, imp in importance[:10]:
        print(f"  {fname}: {imp}")
    
    return model


# ============ Step 4: 验证 ============
def verify():
    print("\n" + "=" * 60)
    print("Step 4: 验证")
    print("=" * 60)
    
    import lightgbm as lgb
    
    # 1. 数据量
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, interval, COUNT(*) FROM kline_data WHERE symbol='au9999' GROUP BY symbol, interval ORDER BY interval")
    for row in cursor.fetchall():
        print(f"  {row[0]} {row[1]}: {row[2]} rows")
    conn.close()
    
    # 2. 模型特征数
    model = lgb.Booster(model_file=r'models\lgbm_model.txt')
    print(f"  Model features: {len(model.feature_name())}")
    
    # 3. 用 au2606 跑一次预测
    from quant.signal_generator.ml_predictor import MLPredictor
    conn = psycopg2.connect(**DB_PARAMS)
    df = pd.read_sql("""
        SELECT time as timestamp, symbol, interval, open, high, low, close, volume, open_interest
        FROM kline_data WHERE symbol='au2606' AND interval='30m'
        ORDER BY time DESC LIMIT 100
    """, conn)
    conn.close()
    
    df = df.sort_values('timestamp').reset_index(drop=True)
    for col in ['open', 'high', 'low', 'close', 'volume', 'open_interest']:
        df[col] = df[col].astype(float)
    
    predictor = MLPredictor()
    result = predictor.predict(df)
    print(f"  Prediction on au2606: signal={result['signal']}, confidence={result['confidence']:.4f}, prediction={result['prediction']:.6f}")
    print("\nDONE!")


if __name__ == '__main__':
    t0 = time.time()
    
    import_1m_data()
    aggregate_15m()
    retrain_model()
    verify()
    
    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s ({elapsed/60:.1f}min)")
