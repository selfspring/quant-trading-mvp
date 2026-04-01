"""
精简特征回归模型训练
~18个精选特征，目标：未来2小时（4根30m）收益率
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
from quant.signal_generator.feature_engineer import FeatureEngineer

logging.basicConfig(level=logging.WARNING, force=True)

# 精选特征
SELECTED_FEATURES = [
    # 价格位置
    'close', 'bb_position',
    # 动量
    'returns_5', 'returns_20', 'rsi',
    # 趋势
    'macd_hist', 'ma_cross_5_20',
    # 波动率
    'atr', 'volatility_10',
    # 成交量
    'volume_ratio_5', 'oi_change', 'oi_volume_ratio',
    # 形态
    'body_ratio', 'upper_shadow', 'lower_shadow',
]

MACRO_FEATURES = [
    'us_10y', 'shibor_1w', 'hold_long_chg', 'hold_long_short_ratio',
]


def load_data():
    with db_engine(config) as engine:
        df = pd.read_sql("""
            SELECT time as timestamp, open, high, low, close, volume, open_interest
            FROM kline_data WHERE symbol='au_main' AND interval='30m'
            ORDER BY time
        """, engine)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def load_macro():
    with db_engine(config) as engine:
        macro = pd.read_sql("SELECT date, indicator, value FROM macro_daily ORDER BY date", engine)
        holding = pd.read_sql("SELECT * FROM fut_holding ORDER BY trade_date", engine)

    # 日频宏观 -> 宽表
    pivot = macro.pivot_table(index='date', columns='indicator', values='value', aggfunc='first')
    pivot.index = pd.to_datetime(pivot.index)

    # 持仓聚合
    if len(holding) > 0:
        daily_hold = holding.groupby('trade_date').agg(
            total_long=('long_hld', 'sum'),
            total_short=('short_hld', 'sum'),
            long_chg=('long_chg', 'sum'),
        ).reset_index()
        daily_hold['long_short_ratio'] = daily_hold['total_long'] / daily_hold['total_short'].replace(0, 1)
        daily_hold['trade_date'] = pd.to_datetime(daily_hold['trade_date'], format='%Y%m%d')
        daily_hold = daily_hold.set_index('trade_date')
    else:
        daily_hold = pd.DataFrame()

    return pivot, daily_hold


def build_features(df, macro_pivot, holding):
    # 技术指标
    fe = FeatureEngineer()
    feat = fe.generate_features(df.copy())

    # 只保留精选技术特征
    available_tech = [c for c in SELECTED_FEATURES if c in feat.columns]
    result = feat[available_tech].copy()
    result['timestamp'] = feat['timestamp'] if 'timestamp' in feat.columns else df.loc[feat.index, 'timestamp']

    # 加宏观
    result['date'] = pd.to_datetime(result['timestamp']).dt.tz_localize(None).dt.normalize()

    # 美债+SHIBOR
    for col in ['us_10y', 'shibor_1w']:
        if col in macro_pivot.columns:
            macro_sub = macro_pivot[[col]].dropna().reset_index()
            macro_sub.columns = ['date', col]
            macro_sub['date'] = pd.to_datetime(macro_sub['date'])
            result = pd.merge_asof(result.sort_values('date'), macro_sub.sort_values('date'),
                                   on='date', direction='backward')

    # 持仓
    if len(holding) > 0:
        hold_sub = holding[['long_chg', 'long_short_ratio']].reset_index()
        hold_sub.columns = ['date', 'hold_long_chg', 'hold_long_short_ratio']
        hold_sub['date'] = pd.to_datetime(hold_sub['date'])
        result = pd.merge_asof(result.sort_values('date'), hold_sub.sort_values('date'),
                               on='date', direction='backward')

    result = result.drop(columns=['date', 'timestamp'], errors='ignore')
    return result


def main():
    print("=" * 70)
    print("  LEAN REGRESSION MODEL")
    print("=" * 70)

    # 加载
    df = load_data()
    macro_pivot, holding = load_macro()
    print(f"30m bars: {len(df)}")

    # 特征
    features = build_features(df, macro_pivot, holding)
    feat_cols = [c for c in features.columns]
    print(f"Features ({len(feat_cols)}): {feat_cols}")

    # 目标：未来4根K线（2小时）收益率
    close = df.loc[features.index, 'close'].values
    horizons = [1, 2, 4]

    for h in horizons:
        if h > 1:
            target = np.log(close[h:] / close[:-h])
            X = features.iloc[:-h]
        else:
            target = np.log(close[1:] / close[:-1])
            X = features.iloc[:-1]

        # 去掉 NaN 行
        valid = ~(X.isna().any(axis=1) | np.isnan(target))
        X = X[valid]
        target = target[valid]

        split = int(len(X) * 0.7)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = target[:split], target[split:]

        # 训练
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

        params = {
            'objective': 'regression',
            'metric': 'mse',
            'num_leaves': 15,
            'learning_rate': 0.03,
            'feature_fraction': 0.7,
            'bagging_fraction': 0.7,
            'bagging_freq': 5,
            'lambda_l1': 0.5,
            'lambda_l2': 0.5,
            'min_data_in_leaf': 50,
            'verbose': -1,
        }

        model = lgb.train(params, train_data, num_boost_round=1000,
                          valid_sets=[valid_data],
                          callbacks=[lgb.early_stopping(80), lgb.log_evaluation(0)])

        preds = model.predict(X_test)
        mse = mean_squared_error(y_test, preds)
        corr = np.corrcoef(y_test, preds)[0, 1] if np.std(preds) > 1e-10 else 0
        direction = np.mean(np.sign(preds) == np.sign(y_test))

        print(f"\n--- Horizon = {h} bars ({h*30}min) ---")
        print(f"  Train: {len(X_train)}, Test: {len(X_test)}")
        print(f"  Best iter: {model.best_iteration}")
        print(f"  MSE: {mse:.8f}, RMSE: {np.sqrt(mse):.6f}")
        print(f"  Corr: {corr:.4f}, Direction: {direction:.4f}")
        print(f"  Pred: mean={preds.mean():.6f}, std={preds.std():.6f}")
        print(f"  Actual: mean={y_test.mean():.6f}, std={y_test.std():.6f}")

        # 信号
        for t in [0.001, 0.002, 0.003, 0.005]:
            buy = (preds > t).sum()
            sell = (preds < -t).sum()
            print(f"  Threshold {t}: buy={buy}, sell={sell}, total={buy+sell}")

        # 特征重要度
        importance = sorted(zip(feat_cols, model.feature_importance()), key=lambda x: -x[1])
        print(f"  Feature importance:")
        for name, imp in importance:
            print(f"    {name}: {imp}")

        # 保存最佳模型（horizon=4）
        if h == 4:
            model.save_model('models/lgbm_model_v2.txt')
            print(f"  Saved to models/lgbm_model_v2.txt")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
