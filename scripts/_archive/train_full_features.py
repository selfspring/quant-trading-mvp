"""
完整特征训练：47技术指标 + 10微观特征 + 基本面宏观特征
主数据：au_main 30m (10000根)
1m数据：多合约直接按时间匹配（不拼接，不做价差调整）
基本面：日频向前填充到30m
"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

import logging
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_squared_error

from quant.common.config import config
from quant.common.db import db_engine

logging.basicConfig(level=logging.WARNING, force=True)


def load_30m():
    with db_engine(config) as engine:
        df = pd.read_sql("""
            SELECT time as timestamp, open, high, low, close, volume, open_interest
            FROM kline_data WHERE symbol='au_main' AND interval='30m'
            ORDER BY time
        """, engine)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def load_1m_all():
    """加载所有合约的1m数据，按时间排序"""
    with db_engine(config) as engine:
        df = pd.read_sql("""
            SELECT time as timestamp, symbol, open, high, low, close, volume, open_interest
            FROM kline_data
            WHERE interval='1m'
              AND symbol IN ('au2504','au2506','au2508','au2510','au2512','au_main','au2606')
            ORDER BY time
        """, engine)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def load_macro_daily():
    with db_engine(config) as engine:
        df = pd.read_sql("SELECT date, indicator, value FROM macro_daily ORDER BY date", engine)
    # 转宽表
    pivot = df.pivot_table(index='date', columns='indicator', values='value', aggfunc='first')
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.sort_index()
    return pivot


def load_fut_holding():
    with db_engine(config) as engine:
        df = pd.read_sql("SELECT * FROM fut_holding ORDER BY trade_date", engine)
    if len(df) == 0:
        return pd.DataFrame()
    # 按日期聚合：总多头、总空头、多空比
    daily = df.groupby('trade_date').agg(
        total_long=('long_hld', 'sum'),
        total_short=('short_hld', 'sum'),
        long_chg=('long_chg', 'sum'),
        short_chg=('short_chg', 'sum'),
    ).reset_index()
    daily['long_short_ratio'] = daily['total_long'] / daily['total_short'].replace(0, 1)
    daily['trade_date'] = pd.to_datetime(daily['trade_date'], format='%Y%m%d')
    daily = daily.set_index('trade_date').sort_index()
    return daily


def load_macro_monthly():
    with db_engine(config) as engine:
        df = pd.read_sql("SELECT month, indicator, value FROM macro_monthly ORDER BY month", engine)
    if len(df) == 0:
        return pd.DataFrame()
    # 只取关键指标
    key_indicators = ['nt_yoy', 'ppi_yoy', 'm2_yoy']
    df_filtered = df[df['indicator'].isin(key_indicators)]
    if len(df_filtered) == 0:
        # 尝试其他列名
        print(f"  Available monthly indicators: {df['indicator'].unique()[:20]}")
        return pd.DataFrame()
    pivot = df_filtered.pivot_table(index='month', columns='indicator', values='value', aggfunc='first')
    # month 格式可能是 202601，转为日期
    pivot.index = pd.to_datetime(pivot.index, format='%Y%m', errors='coerce')
    pivot = pivot.dropna(how='all').sort_index()
    return pivot


def compute_micro_features(df_30m, df_1m):
    """对每根30m K线，从1m数据中提取微观特征"""
    print(f"  Computing micro features: {len(df_30m)} bars x {len(df_1m)} 1m bars")

    # 建立1m数据的时间索引，加速查找
    df_1m = df_1m.sort_values('timestamp').reset_index(drop=True)
    df_1m['ts_val'] = df_1m['timestamp'].values.astype(np.int64)

    micro_cols = ['micro_vol_std', 'micro_vol_ratio', 'micro_range_mean', 'micro_range_std',
                  'micro_up_ratio', 'micro_close_slope', 'micro_vwap_diff',
                  'micro_max_vol_bar', 'micro_oi_change', 'micro_tail_momentum']

    results = {c: [] for c in micro_cols}

    matched = 0
    for _, row in df_30m.iterrows():
        t_start = row['timestamp']
        t_end = t_start + pd.Timedelta(minutes=30)

        mask = (df_1m['timestamp'] >= t_start) & (df_1m['timestamp'] < t_end)
        bars = df_1m.loc[mask]

        if len(bars) < 5:
            for c in micro_cols:
                results[c].append(np.nan)
            continue

        matched += 1
        closes = bars['close'].values
        volumes = bars['volume'].values
        highs = bars['high'].values
        lows = bars['low'].values
        oi = bars['open_interest'].values

        # 1. 成交量标准差
        results['micro_vol_std'].append(np.std(volumes))
        # 2. 量能加速：最后5根 vs 前面
        if len(bars) > 5:
            tail_vol = volumes[-5:].mean()
            head_vol = volumes[:-5].mean() if volumes[:-5].mean() > 0 else 1
            results['micro_vol_ratio'].append(tail_vol / head_vol)
        else:
            results['micro_vol_ratio'].append(1.0)
        # 3. 微观波动率均值
        ranges = highs - lows
        results['micro_range_mean'].append(np.mean(ranges))
        # 4. 微观波动率标准差
        results['micro_range_std'].append(np.std(ranges))
        # 5. 涨跌比
        up = np.sum(closes[1:] > closes[:-1])
        results['micro_up_ratio'].append(up / max(len(closes) - 1, 1))
        # 6. 收盘价斜率
        x = np.arange(len(closes))
        if np.std(closes) > 0:
            slope = np.polyfit(x, closes, 1)[0]
        else:
            slope = 0
        results['micro_close_slope'].append(slope)
        # 7. VWAP偏离
        if volumes.sum() > 0:
            vwap = np.sum(closes * volumes) / volumes.sum()
            results['micro_vwap_diff'].append((closes[-1] - vwap) / vwap if vwap > 0 else 0)
        else:
            results['micro_vwap_diff'].append(0)
        # 8. 最大成交量位置
        results['micro_max_vol_bar'].append(np.argmax(volumes) / max(len(volumes) - 1, 1))
        # 9. 持仓量变化
        results['micro_oi_change'].append(oi[-1] - oi[0] if len(oi) > 0 else 0)
        # 10. 尾部动量
        if len(closes) >= 5 and closes[-5] > 0:
            results['micro_tail_momentum'].append((closes[-1] - closes[-5]) / closes[-5])
        else:
            results['micro_tail_momentum'].append(0)

    print(f"  Matched {matched}/{len(df_30m)} bars with 1m data")

    for c in micro_cols:
        df_30m[c] = results[c]

    return df_30m


def add_macro_features(df_30m, macro_daily, fut_holding, macro_monthly):
    """将宏观数据向前填充到30m K线"""
    df = df_30m.copy()
    df['date'] = df['timestamp'].dt.date
    df['date'] = pd.to_datetime(df['date'])

    added = 0

    # 日频宏观数据
    if len(macro_daily) > 0:
        # 选关键列
        key_daily = []
        for col in ['us_10y', 'us_2y', 'us_5y', 'shibor_on', 'shibor_1w']:
            if col in macro_daily.columns:
                key_daily.append(col)
        if key_daily:
            macro_sub = macro_daily[key_daily].copy()
            macro_sub.index.name = 'date'
            macro_sub = macro_sub.reset_index()
            macro_sub['date'] = pd.to_datetime(macro_sub['date'])
            df = pd.merge_asof(df.sort_values('date'), macro_sub.sort_values('date'),
                               on='date', direction='backward')
            added += len(key_daily)
            # 期限利差
            if 'us_10y' in df.columns and 'us_2y' in df.columns:
                df['us_spread_10y_2y'] = df['us_10y'] - df['us_2y']
                added += 1
            print(f"  Added {len(key_daily)} daily macro features")

    # 持仓排名
    if len(fut_holding) > 0:
        holding = fut_holding.reset_index()
        holding.columns = ['date'] + [f'hold_{c}' for c in fut_holding.columns]
        holding['date'] = pd.to_datetime(holding['date'])
        df = pd.merge_asof(df.sort_values('date'), holding.sort_values('date'),
                           on='date', direction='backward')
        added += len(fut_holding.columns)
        print(f"  Added {len(fut_holding.columns)} holding features")

    # 月度宏观
    if len(macro_monthly) > 0:
        monthly = macro_monthly.reset_index()
        monthly.columns = ['date'] + [f'macro_{c}' for c in macro_monthly.columns]
        monthly['date'] = pd.to_datetime(monthly['date'])
        monthly = monthly.dropna(subset=['date'])  # 去除 NaT
        if len(monthly) > 0:
            df = pd.merge_asof(df.sort_values('date'), monthly.sort_values('date'),
                               on='date', direction='backward')
            added += len(macro_monthly.columns)
            print(f"  Added {len(macro_monthly.columns)} monthly macro features")

    df = df.drop(columns=['date'], errors='ignore')
    print(f"  Total macro features added: {added}")
    return df


def generate_technical_features(df):
    """生成47个技术指标特征"""
    from quant.signal_generator.feature_engineer import FeatureEngineer
    fe = FeatureEngineer()
    return fe.generate_features(df.copy())


def train_and_evaluate(X_train, y_train, X_test, y_test, label, save_path=None):
    train_data = lgb.Dataset(X_train, label=y_train)
    valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    params = {
        'objective': 'regression',
        'metric': 'mse',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'lambda_l1': 0.1,
        'lambda_l2': 0.1,
        'verbose': -1,
    }

    model = lgb.train(params, train_data, num_boost_round=500,
                      valid_sets=[valid_data],
                      callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)])

    preds = model.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    corr = np.corrcoef(y_test, preds)[0, 1] if np.std(preds) > 1e-10 else 0
    direction = np.mean(np.sign(preds) == np.sign(y_test))

    print(f"\n=== {label} ===")
    print(f"  Features: {X_train.shape[1]}")
    print(f"  Train: {len(X_train)}, Test: {len(X_test)}")
    print(f"  Best iteration: {model.best_iteration}")
    print(f"  MSE: {mse:.8f}, RMSE: {np.sqrt(mse):.6f}")
    print(f"  Correlation: {corr:.4f}")
    print(f"  Direction accuracy: {direction:.4f}")
    print(f"  Pred: mean={preds.mean():.6f}, std={preds.std():.6f}")
    print(f"  Actual: mean={y_test.mean():.6f}, std={y_test.std():.6f}")

    # 信号统计
    threshold = 0.003
    buy = (preds > threshold).sum()
    sell = (preds < -threshold).sum()
    print(f"  Signals (>{threshold}): buy={buy}, sell={sell}, neutral={len(preds)-buy-sell}")

    if save_path:
        model.save_model(save_path)
        print(f"  Model saved to {save_path}")

    # Top 15 feature importance
    importance = sorted(zip(X_train.columns, model.feature_importance()), key=lambda x: -x[1])
    print(f"  Top 15 features:")
    for name, imp in importance[:15]:
        print(f"    {name}: {imp}")

    return model, preds


def main():
    print("=" * 80)
    print("  FULL FEATURE TRAINING")
    print("  47 technical + 10 micro + macro fundamentals")
    print("=" * 80)

    # 1. 加载数据
    print("\n[1] Loading data...")
    df_30m = load_30m()
    df_1m = load_1m_all()
    macro_daily = load_macro_daily()
    fut_holding = load_fut_holding()
    macro_monthly = load_macro_monthly()

    print(f"  30m: {len(df_30m)} bars ({df_30m.timestamp.min()} ~ {df_30m.timestamp.max()})")
    print(f"  1m: {len(df_1m)} bars")
    print(f"  Macro daily: {len(macro_daily)} days, {len(macro_daily.columns)} indicators")
    print(f"  Fut holding: {len(fut_holding)} days")
    print(f"  Macro monthly: {len(macro_monthly)} months")

    # 2. 技术指标特征
    print("\n[2] Generating technical features...")
    features_df = generate_technical_features(df_30m)
    exclude_cols = ['timestamp', 'datetime', 'symbol', 'id', 'duration']
    tech_cols = [c for c in features_df.columns if c not in exclude_cols]
    print(f"  Technical features: {len(tech_cols)}")

    # 3. 微观特征
    print("\n[3] Computing micro features...")
    features_df = compute_micro_features(features_df, df_1m)
    micro_cols = [c for c in features_df.columns if c.startswith('micro_')]
    print(f"  Micro features: {len(micro_cols)}")

    # 4. 宏观特征
    print("\n[4] Adding macro features...")
    features_df = add_macro_features(features_df, macro_daily, fut_holding, macro_monthly)
    all_cols = [c for c in features_df.columns if c not in exclude_cols
                and c not in ['open', 'high', 'low', 'close', 'volume', 'open_interest', 'timestamp']]
    macro_added = [c for c in all_cols if c not in tech_cols and c not in micro_cols]
    print(f"  Macro features: {len(macro_added)}")
    print(f"  Total features: {len(all_cols)}")

    # 5. 目标变量
    print("\n[5] Preparing target...")
    close = df_30m.loc[features_df.index, 'close'].values
    target = np.log(close[1:] / close[:-1])
    features_df = features_df.iloc[:-1]

    # 6. 70/30 分割
    split = int(len(features_df) * 0.7)
    print(f"  Train: {split}, Test: {len(features_df) - split}")

    # 7. 训练对比
    print("\n[6] Training models...")

    # A: 基线（只有技术指标）
    X_base = features_df[tech_cols]
    train_and_evaluate(X_base.iloc[:split], target[:split],
                       X_base.iloc[split:], target[split:],
                       "Baseline (technical only)")

    # B: 技术 + 微观
    tech_micro_cols = tech_cols + micro_cols
    X_tm = features_df[tech_micro_cols]
    train_and_evaluate(X_tm.iloc[:split], target[:split],
                       X_tm.iloc[split:], target[split:],
                       "Technical + Micro")

    # C: 全部特征
    X_full = features_df[all_cols]
    train_and_evaluate(X_full.iloc[:split], target[:split],
                       X_full.iloc[split:], target[split:],
                       "FULL (tech + micro + macro)",
                       save_path='models/lgbm_model_v2.txt')

    print("\n" + "=" * 80)
    print("  DONE")
    print("=" * 80)


if __name__ == '__main__':
    main()
