"""
训练脚本：对比有/无微观特征的 LightGBM 模型
"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

import logging
import numpy as np
import pandas as pd
import lightgbm as lgb

from quant.common.config import config
from quant.common.db import db_engine
from quant.signal_generator.feature_engineer import FeatureEngineer

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

NON_FEATURE_COLS = ['timestamp', 'datetime', 'symbol', 'id', 'duration']


def load_30m_data():
    """加载 au2606 30m 数据"""
    sql = (
        "SELECT time AS timestamp, open, high, low, close, volume, open_interest "
        "FROM kline_data "
        "WHERE symbol='au2606' AND interval='30m' "
        "ORDER BY time"
    )
    with db_engine(config) as engine:
        df = pd.read_sql(sql, engine)
    logger.info("Loaded %d 30m bars", len(df))
    return df


def build_dataset(df, include_micro):
    """生成特征和目标变量"""
    fe = FeatureEngineer(include_micro=include_micro)
    df_feat = fe.generate_features(df.copy())

    # 目标: log(close_{t+1} / close_t)
    df_feat['target'] = np.log(df_feat['close'].shift(-1) / df_feat['close'])

    # 去掉 NaN
    df_feat = df_feat.dropna()

    # 分离
    y = df_feat['target']
    drop_cols = [c for c in NON_FEATURE_COLS + ['target'] if c in df_feat.columns]
    X = df_feat.drop(columns=drop_cols)

    # 只保留数值列
    X = X.select_dtypes(include=[np.number])

    return X, y


def train_and_evaluate(X, y, test_ratio=0.3, label=""):
    """时间序列分割 + LightGBM 训练 + 评估"""
    split = int(len(X) * (1 - test_ratio))
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    logger.info("[%s] Train: %d, Test: %d, Features: %d", label, len(X_train), len(X_test), X_train.shape[1])

    params = {
        'objective': 'regression',
        'metric': 'mse',
        'learning_rate': config.ml.learning_rate,
        'num_leaves': config.ml.num_leaves,
        'max_depth': config.ml.max_depth,
        'min_data_in_leaf': config.ml.min_data_in_leaf,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
    }

    train_set = lgb.Dataset(X_train, label=y_train)
    val_set = lgb.Dataset(X_test, label=y_test, reference=train_set)

    model = lgb.train(
        params,
        train_set,
        num_boost_round=500,
        valid_sets=[val_set],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
    )

    # 预测
    y_pred = model.predict(X_test)

    # 评估
    mse = np.mean((y_test.values - y_pred) ** 2)
    rmse = np.sqrt(mse)
    corr = np.corrcoef(y_test.values, y_pred)[0, 1]
    direction_acc = np.mean((y_test.values > 0) == (y_pred > 0))

    print(f"\n{'='*60}")
    print(f"  Model: {label}")
    print(f"{'='*60}")
    print(f"  Features:       {X_train.shape[1]}")
    print(f"  Train size:     {len(X_train)}")
    print(f"  Test size:      {len(X_test)}")
    print(f"  MSE:            {mse:.8f}")
    print(f"  RMSE:           {rmse:.6f}")
    print(f"  Correlation:    {corr:.4f}")
    print(f"  Direction Acc:  {direction_acc:.4f} ({direction_acc*100:.1f}%)")
    print(f"  Pred mean:      {y_pred.mean():.6f}")
    print(f"  Pred std:       {y_pred.std():.6f}")
    print(f"  Pred min/max:   {y_pred.min():.6f} / {y_pred.max():.6f}")
    print(f"  Actual mean:    {y_test.mean():.6f}")
    print(f"  Actual std:     {y_test.std():.6f}")

    # 特征重要性 top 15
    importance = model.feature_importance(importance_type='gain')
    feat_imp = sorted(zip(X_train.columns, importance), key=lambda x: -x[1])
    print(f"\n  Top 15 features:")
    for i, (name, imp) in enumerate(feat_imp[:15]):
        print(f"    {i+1:2d}. {name:<30s} {imp:.1f}")

    return model, {
        'mse': mse, 'rmse': rmse, 'corr': corr,
        'direction_acc': direction_acc,
        'pred_mean': y_pred.mean(), 'pred_std': y_pred.std(),
    }


def main():
    print("=" * 60)
    print("  TRAIN WITH MICRO FEATURES")
    print("=" * 60)

    df_30m = load_30m_data()

    # --- 新模型: 有微观特征 ---
    print("\n[1] Building micro dataset...")
    X_micro, y_micro = build_dataset(df_30m, include_micro=True)
    model_micro, metrics_micro = train_and_evaluate(X_micro, y_micro, label="Micro (57 features)")

    # --- Baseline on same time window (fair comparison) ---
    print("\n[2] Building baseline on same time window...")
    # 用 micro 数据集的 index 来截取 baseline，保证同样的时间段
    X_base_full, y_base_full = build_dataset(df_30m, include_micro=False)
    common_idx = X_micro.index.intersection(X_base_full.index)
    X_base = X_base_full.loc[common_idx]
    y_base = y_base_full.loc[common_idx]
    model_base, metrics_base = train_and_evaluate(X_base, y_base, label="Baseline same window (47 features)")

    # --- Baseline: 全量数据 ---
    print("\n[3] Baseline on full 30m data...")
    _, metrics_base_full = train_and_evaluate(X_base_full, y_base_full, label="Baseline full (47 features)")

    # 保存新模型
    model_path = "E:/quant-trading-mvp/models/lgbm_model_micro.txt"
    model_micro.save_model(model_path)
    print(f"\nMicro model saved to: {model_path}")

    # --- 对比 ---
    print(f"\n{'='*60}")
    print(f"  COMPARISON")
    print(f"{'='*60}")
    print(f"  {'Metric':<20s} {'Base(same)':>12s} {'Micro':>12s} {'Base(full)':>12s}")
    print(f"  {'-'*56}")
    for key in ['mse', 'rmse', 'corr', 'direction_acc', 'pred_std']:
        b = metrics_base[key]
        m = metrics_micro[key]
        f = metrics_base_full[key]
        print(f"  {key:<20s} {b:>12.6f} {m:>12.6f} {f:>12.6f}")

    print(f"{'='*60}")


if __name__ == "__main__":
    main()
