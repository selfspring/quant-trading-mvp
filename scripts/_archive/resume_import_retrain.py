"""
续传导入：从已有数据之后继续，然后聚合+训练
"""
import os, sys, glob, time, gc
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, r'E:\quant-trading-mvp')

DB_PARAMS = dict(host='localhost', port=5432, dbname='quant_trading',
                 user='postgres', password='@Cmx1454697261')

def get_db_count(symbol, interval):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM kline_data WHERE symbol=%s AND interval=%s", (symbol, interval))
    n = cur.fetchone()[0]
    conn.close()
    return n

def import_one_file(fpath):
    """导入单个文件，独立连接"""
    fname = os.path.basename(fpath)
    
    df = pd.read_csv(fpath, low_memory=False)
    df.rename(columns={'Unnamed: 0': 'time'}, inplace=True)
    
    cols = ['time', 'open', 'high', 'low', 'close', 'volume', 'open_interest']
    df = df[cols].copy()
    df = df.dropna(subset=['open', 'close'])
    
    if df.empty:
        print(f"  {fname}: 0 valid rows, skip")
        return 0
    
    df['open_interest'] = df['open_interest'].fillna(0)
    df['volume'] = df['volume'].fillna(0)
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize('Asia/Shanghai')
    
    # 检查已有数据，跳过已导入的时间范围
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # 获取该文件时间范围内已有的时间点
    t_min = df['time'].min()
    t_max = df['time'].max()
    cur.execute(
        "SELECT COUNT(*) FROM kline_data WHERE symbol='au9999' AND interval='1m' AND time >= %s AND time <= %s",
        (t_min, t_max)
    )
    already = cur.fetchone()[0]
    
    if already >= len(df) * 0.95:  # 95% 已存在则跳过
        print(f"  {fname}: {already} already in DB, skip")
        conn.close()
        return already
    
    batch_size = 2000
    inserted = 0
    
    for start in range(0, len(df), batch_size):
        batch = df.iloc[start:start + batch_size]
        values = [
            (row['time'], 'au9999', '1m',
             float(row['open']), float(row['high']), float(row['low']),
             float(row['close']), float(row['volume']), float(row['open_interest']))
            for _, row in batch.iterrows()
        ]
        try:
            execute_values(cur, """
                INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
                VALUES %s ON CONFLICT DO NOTHING
            """, values)
            conn.commit()
            inserted += len(values)
        except Exception as e:
            conn.rollback()
            print(f"    ERROR batch {start}: {e}")
    
    conn.close()
    del df
    gc.collect()
    
    print(f"  {fname}: {inserted} inserted")
    return inserted


def import_remaining():
    print("=" * 60)
    print("Step 1: 续传导入缺失文件")
    print("=" * 60)
    
    files = sorted(glob.glob(r'data\raw_gold\**\AU9999*.csv', recursive=True))
    total = 0
    for fpath in files:
        n = import_one_file(fpath)
        total += n
        print(f"    Running total: {total:,}")
    
    final = get_db_count('au9999', '1m')
    print(f"\nFinal DB count (au9999 1m): {final:,}")
    return final


def aggregate_15m():
    print("\n" + "=" * 60)
    print("Step 2: 聚合 15m K 线")
    print("=" * 60)
    
    conn = psycopg2.connect(**DB_PARAMS)
    
    # 分批读取避免 OOM（按年份）
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT EXTRACT(year FROM time)::int FROM kline_data WHERE symbol='au9999' AND interval='1m' ORDER BY 1")
    years = [r[0] for r in cur.fetchall()]
    print(f"Processing years: {years}")
    
    all_15m = []
    
    for year in years:
        df = pd.read_sql(
            "SELECT time, open, high, low, close, volume, open_interest "
            "FROM kline_data WHERE symbol='au9999' AND interval='1m' "
            "AND EXTRACT(year FROM time)=%s ORDER BY time",
            conn, params=(year,)
        )
        df['time'] = pd.to_datetime(df['time'], utc=True).dt.tz_convert('Asia/Shanghai')
        df = df.set_index('time')
        for col in ['open','high','low','close','volume','open_interest']:
            df[col] = df[col].astype(float)
        
        df_15 = df.resample('15min', label='left', closed='left').agg(
            {'open':'first','high':'max','low':'min','close':'last','volume':'sum','open_interest':'last'}
        ).dropna(subset=['open','close'])
        df_15 = df_15[df_15['volume'] > 0]
        all_15m.append(df_15)
        print(f"  {year}: {len(df_15)} 15m bars")
        del df, df_15
        gc.collect()
    
    conn.close()
    
    df_all = pd.concat(all_15m).reset_index()
    del all_15m
    gc.collect()
    print(f"Total 15m bars: {len(df_all):,}")
    
    # 写入
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    batch_size = 5000
    inserted = 0
    for start in range(0, len(df_all), batch_size):
        batch = df_all.iloc[start:start+batch_size]
        values = [
            (row['time'], 'au9999', '15m',
             float(row['open']), float(row['high']), float(row['low']),
             float(row['close']), float(row['volume']), float(row['open_interest']))
            for _, row in batch.iterrows()
        ]
        execute_values(cur, """
            INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
            VALUES %s ON CONFLICT DO NOTHING
        """, values)
        conn.commit()
        inserted += len(values)
    
    conn.close()
    final = get_db_count('au9999', '15m')
    print(f"Inserted {inserted}, DB total 15m: {final:,}")
    return final


def retrain_model():
    print("\n" + "=" * 60)
    print("Step 3: 重训模型")
    print("=" * 60)
    
    import lightgbm as lgb
    import shutil
    from quant.signal_generator.feature_engineer import FeatureEngineer
    
    model_path = r'models\lgbm_model.txt'
    if os.path.exists(model_path):
        shutil.copy2(model_path, model_path + '.bak')
        print("Old model backed up")
    
    conn = psycopg2.connect(**DB_PARAMS)
    df = pd.read_sql(
        "SELECT time as timestamp, 'au9999' as symbol, '15m' as interval, "
        "open, high, low, close, volume, open_interest "
        "FROM kline_data WHERE symbol='au9999' AND interval='15m' ORDER BY time",
        conn
    )
    conn.close()
    print(f"15m rows loaded: {len(df):,}")
    
    for col in ['open','high','low','close','volume','open_interest']:
        df[col] = df[col].astype(float)
    
    fe = FeatureEngineer()
    df_feat = fe.generate_features(df)
    print(f"Features: {len(df_feat.columns)} cols, {len(df_feat)} rows")
    
    horizon = 60
    df_feat['target'] = np.log(df_feat['close'].shift(-horizon) / df_feat['close'])
    
    drop_cols = ['timestamp','symbol','interval','open','high','low','close',
                 'volume','open_interest','target','datetime']
    feature_cols = [c for c in df_feat.columns if c not in drop_cols]
    df_clean = df_feat.dropna(subset=['target'] + feature_cols)
    print(f"Clean rows: {len(df_clean):,}, features: {len(feature_cols)}")
    
    X = df_clean[feature_cols].astype(float)
    y = df_clean['target'].astype(float)
    
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    print(f"Train: {len(X_train):,}, Test: {len(X_test):,}")
    
    train_data = lgb.Dataset(X_train, label=y_train)
    valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
    
    params = {
        'objective': 'regression', 'metric': 'mse',
        'num_leaves': 63, 'learning_rate': 0.05,
        'feature_fraction': 0.8, 'bagging_fraction': 0.8,
        'bagging_freq': 5, 'lambda_l1': 0.1, 'lambda_l2': 0.1,
        'verbose': -1
    }
    model = lgb.train(params, train_data, num_boost_round=1000,
                      valid_sets=[valid_data],
                      callbacks=[lgb.log_evaluation(100), lgb.early_stopping(50)])
    
    model.save_model(model_path)
    print(f"Model saved: {model_path}")
    
    y_pred = model.predict(X_test)
    mse = float(np.mean((y_test - y_pred)**2))
    corr = float(np.corrcoef(y_test, y_pred)[0,1])
    dir_acc = float(np.mean(np.sign(y_test) == np.sign(y_pred)))
    print(f"MSE={mse:.6f}, Corr={corr:.4f}, DirAcc={dir_acc:.4%}, Features={len(model.feature_name())}")


if __name__ == '__main__':
    t0 = time.time()
    import_remaining()
    aggregate_15m()
    retrain_model()
    print(f"\nTotal: {time.time()-t0:.0f}s")
