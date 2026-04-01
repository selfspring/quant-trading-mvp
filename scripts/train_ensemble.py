"""
集成模型训练脚本
训练 LightGBM + XGBoost + CatBoost 三模型

模型保存路径：
- models/lgbm_model.txt
- models/xgb_model.json
- models/catboost_model.cbm
"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

import logging
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error

from quant.common.config import config
from quant.common.db import db_engine
from quant.signal_generator.feature_engineer import FeatureEngineer

logging.basicConfig(level=logging.WARNING, force=True)


def load_30m():
    """加载 30m 主 K 线数据"""
    with db_engine(config) as engine:
        df = pd.read_sql("""
            SELECT time as timestamp, open, high, low, close, volume, open_interest
            FROM kline_data WHERE symbol='au_main' AND interval='30m'
            ORDER BY time
        """, engine)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def load_1m_all():
    """加载所有合约的 1m 数据"""
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
    """加载日频宏观数据"""
    with db_engine(config) as engine:
        df = pd.read_sql("SELECT date, indicator, value FROM macro_daily ORDER BY date", engine)
    pivot = df.pivot_table(index='date', columns='indicator', values='value', aggfunc='first')
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.sort_index()
    return pivot


def load_fut_holding():
    """加载期货持仓排名数据"""
    with db_engine(config) as engine:
        df = pd.read_sql("SELECT * FROM fut_holding ORDER BY trade_date", engine)
    if len(df) == 0:
        return pd.DataFrame()
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
    """加载月频宏观数据"""
    with db_engine(config) as engine:
        df = pd.read_sql("SELECT month, indicator, value FROM macro_monthly ORDER BY month", engine)
    if len(df) == 0:
        return pd.DataFrame()
    key_indicators = ['nt_yoy', 'ppi_yoy', 'm2_yoy']
    df_filtered = df[df['indicator'].isin(key_indicators)]
    if len(df_filtered) == 0:
        return pd.DataFrame()
    pivot = df_filtered.pivot_table(index='month', columns='indicator', values='value', aggfunc='first')
    pivot.index = pd.to_datetime(pivot.index, format='%Y%m', errors='coerce')
    pivot = pivot.dropna(how='all').sort_index()
    return pivot


def compute_micro_features(df_30m, df_1m):
    """计算微观特征"""
    print(f"  计算微观特征：{len(df_30m)} 根 30m K 线 x {len(df_1m)} 根 1m K 线")

    df_1m = df_1m.sort_values('timestamp').reset_index(drop=True)

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

        results['micro_vol_std'].append(np.std(volumes))
        
        if len(bars) > 5:
            tail_vol = volumes[-5:].mean()
            head_vol = volumes[:-5].mean() if volumes[:-5].mean() > 0 else 1
            results['micro_vol_ratio'].append(tail_vol / head_vol)
        else:
            results['micro_vol_ratio'].append(1.0)
        
        ranges = highs - lows
        results['micro_range_mean'].append(np.mean(ranges))
        results['micro_range_std'].append(np.std(ranges))
        
        up = np.sum(closes[1:] > closes[:-1])
        results['micro_up_ratio'].append(up / max(len(closes) - 1, 1))
        
        x = np.arange(len(closes))
        if np.std(closes) > 0:
            slope = np.polyfit(x, closes, 1)[0]
        else:
            slope = 0
        results['micro_close_slope'].append(slope)
        
        if volumes.sum() > 0:
            vwap = np.sum(closes * volumes) / volumes.sum()
            results['micro_vwap_diff'].append((closes[-1] - vwap) / vwap if vwap > 0 else 0)
        else:
            results['micro_vwap_diff'].append(0)
        
        results['micro_max_vol_bar'].append(np.argmax(volumes) / max(len(volumes) - 1, 1))
        results['micro_oi_change'].append(oi[-1] - oi[0] if len(oi) > 0 else 0)
        
        if len(closes) >= 5 and closes[-5] > 0:
            results['micro_tail_momentum'].append((closes[-1] - closes[-5]) / closes[-5])
        else:
            results['micro_tail_momentum'].append(0)

    print(f"  匹配 {matched}/{len(df_30m)} 根 K 线")

    for c in micro_cols:
        df_30m[c] = results[c]

    return df_30m


def add_macro_features(df_30m, macro_daily, fut_holding, macro_monthly):
    """添加宏观特征"""
    df = df_30m.copy()
    df['date'] = df['timestamp'].dt.date
    df['date'] = pd.to_datetime(df['date'])

    added = 0

    if len(macro_daily) > 0:
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
            if 'us_10y' in df.columns and 'us_2y' in df.columns:
                df['us_spread_10y_2y'] = df['us_10y'] - df['us_2y']
                added += 1
            print(f"  添加 {len(key_daily)} 个日频宏观特征")

    if len(fut_holding) > 0:
        holding = fut_holding.reset_index()
        holding.columns = ['date'] + [f'hold_{c}' for c in fut_holding.columns]
        holding['date'] = pd.to_datetime(holding['date'])
        df = pd.merge_asof(df.sort_values('date'), holding.sort_values('date'),
                           on='date', direction='backward')
        added += len(fut_holding.columns)
        print(f"  添加 {len(fut_holding.columns)} 个持仓特征")

    if len(macro_monthly) > 0:
        monthly = macro_monthly.reset_index()
        monthly.columns = ['date'] + [f'macro_{c}' for c in macro_monthly.columns]
        monthly['date'] = pd.to_datetime(monthly['date'])
        monthly = monthly.dropna(subset=['date'])
        if len(monthly) > 0:
            df = pd.merge_asof(df.sort_values('date'), monthly.sort_values('date'),
                               on='date', direction='backward')
            added += len(macro_monthly.columns)
            print(f"  添加 {len(macro_monthly.columns)} 个月频宏观特征")

    df = df.drop(columns=['date'], errors='ignore')
    print(f"  共添加宏观特征：{added} 个")
    return df


def prepare_data():
    """准备训练数据"""
    print("\n[1] 加载数据...")
    df_30m = load_30m()
    df_1m = load_1m_all()
    macro_daily = load_macro_daily()
    fut_holding = load_fut_holding()
    macro_monthly = load_macro_monthly()

    print(f"  30m: {len(df_30m)} 根")
    print(f"  1m: {len(df_1m)} 根")
    print(f"  日频宏观：{len(macro_daily)} 天")
    print(f"  持仓排名：{len(fut_holding)} 天")
    print(f"  月频宏观：{len(macro_monthly)} 月")

    print("\n[2] 生成技术指标特征...")
    fe = FeatureEngineer()
    features_df = fe.generate_features(df_30m.copy())
    exclude_cols = ['timestamp', 'datetime', 'symbol', 'id', 'duration']
    tech_cols = [c for c in features_df.columns if c not in exclude_cols]
    print(f"  技术指标特征：{len(tech_cols)} 个")

    print("\n[3] 计算微观特征...")
    features_df = compute_micro_features(features_df, df_1m)
    micro_cols = [c for c in features_df.columns if c.startswith('micro_')]
    print(f"  微观特征：{len(micro_cols)} 个")

    print("\n[4] 添加宏观特征...")
    features_df = add_macro_features(features_df, macro_daily, fut_holding, macro_monthly)
    all_cols = [c for c in features_df.columns if c not in exclude_cols
                and c not in ['open', 'high', 'low', 'close', 'volume', 'open_interest', 'timestamp']]
    print(f"  总特征数：{len(all_cols)} 个")

    print("\n[5] 准备目标变量...")
    close = df_30m.loc[features_df.index, 'close'].values
    target = np.log(close[1:] / close[:-1])
    features_df = features_df.iloc[:-1]
    X = features_df[all_cols]
    y = target[:len(X)]

    split = int(len(X) * 0.7)
    print(f"  训练集：{split} 样本，测试集：{len(X) - split} 样本")

    return X.iloc[:split], y[:split], X.iloc[split:], y[split:], all_cols


def evaluate_direction(y_true, y_pred, threshold=0.005):
    """计算方向准确率"""
    pred_direction = np.sign(y_pred)
    true_direction = np.sign(y_true)
    return np.mean(pred_direction == true_direction)


def train_lightgbm(X_train, y_train, X_test, y_test):
    """训练 LightGBM 模型"""
    print("\n[6.1] 训练 LightGBM...")
    import lightgbm as lgb

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
    direction_acc = evaluate_direction(y_test, preds)

    print(f"  LightGBM - MSE: {mse:.8f}, 方向准确率：{direction_acc:.4f}")

    save_path = 'models/lgbm_model.txt'
    model.save_model(save_path)
    print(f"  模型已保存：{save_path}")

    return model, preds, direction_acc


def train_xgboost(X_train, y_train, X_test, y_test):
    """训练 XGBoost 模型"""
    print("\n[6.2] 训练 XGBoost...")
    import xgboost as xgb

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)

    params = {
        'objective': 'reg:squarederror',
        'eval_metric': 'rmse',
        'n_estimators': 1000,
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': 42,
    }

    model = xgb.train(params, dtrain, num_boost_round=1000)

    preds = model.predict(dtest)
    mse = mean_squared_error(y_test, preds)
    direction_acc = evaluate_direction(y_test, preds)

    print(f"  XGBoost - MSE: {mse:.8f}, 方向准确率：{direction_acc:.4f}")

    save_path = 'models/xgb_model.json'
    model.save_model(save_path)
    print(f"  模型已保存：{save_path}")

    return model, preds, direction_acc


def train_catboost(X_train, y_train, X_test, y_test):
    """训练 CatBoost 模型"""
    print("\n[6.3] 训练 CatBoost...")
    from catboost import CatBoostRegressor

    model = CatBoostRegressor(
        iterations=1000,
        depth=6,
        learning_rate=0.05,
        loss_function='RMSE',
        verbose=False,
    )

    model.fit(X_train, y_train, eval_set=(X_test, y_test), use_best_model=True)

    preds = model.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    direction_acc = evaluate_direction(y_test, preds)

    print(f"  CatBoost - MSE: {mse:.8f}, 方向准确率：{direction_acc:.4f}")

    save_path = 'models/catboost_model.cbm'
    model.save_model(save_path)
    print(f"  模型已保存：{save_path}")

    return model, preds, direction_acc


def evaluate_ensemble(pred_lgb, pred_xgb, pred_cat, y_test, direction_acc_lgb, direction_acc_xgb, direction_acc_cat):
    """评估集成模型"""
    print("\n[7] 评估集成模型...")

    # 加权平均
    weights = [0.4, 0.3, 0.3]
    ensemble_pred = weights[0] * pred_lgb + weights[1] * pred_xgb + weights[2] * pred_cat

    mse = mean_squared_error(y_test, ensemble_pred)
    direction_acc = evaluate_direction(y_test, ensemble_pred)

    print(f"  集成模型 - MSE: {mse:.8f}, 方向准确率：{direction_acc:.4f}")
    print(f"\n  各模型方向准确率对比:")
    print(f"    LightGBM:  {direction_acc_lgb:.4f}")
    print(f"    XGBoost:   {direction_acc_xgb:.4f}")
    print(f"    CatBoost:  {direction_acc_cat:.4f}")
    print(f"    Ensemble:  {direction_acc:.4f}")

    return direction_acc


def main():
    print("=" * 80)
    print("  集成模型训练")
    print("  LightGBM + XGBoost + CatBoost")
    print("=" * 80)

    # 准备数据
    X_train, y_train, X_test, y_test, all_cols = prepare_data()

    # 训练三个模型
    model_lgb, pred_lgb, dir_acc_lgb = train_lightgbm(X_train, y_train, X_test, y_test)
    model_xgb, pred_xgb, dir_acc_xgb = train_xgboost(X_train, y_train, X_test, y_test)
    model_cat, pred_cat, dir_acc_cat = train_catboost(X_train, y_train, X_test, y_test)

    # 评估集成模型
    ensemble_acc = evaluate_ensemble(pred_lgb, pred_xgb, pred_cat, y_test,
                                      dir_acc_lgb, dir_acc_xgb, dir_acc_cat)

    print("\n" + "=" * 80)
    print("  训练完成")
    print("=" * 80)


if __name__ == '__main__':
    main()
