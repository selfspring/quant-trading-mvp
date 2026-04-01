"""训练脚本：使用 au_continuous 连续合约数据训练 LightGBM"""
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
    sql = (
        "SELECT time AS timestamp, open, high, low, close, volume, open_interest "
        "FROM kline_data "
        "WHERE symbol='au_continuous' AND interval='30m' "
        "ORDER BY time"
    )
    with db_engine(config) as engine:
        df = pd.read_sql(sql, engine)
    logger.info("Loaded %d 30m bars", len(df))
    return df


def main():
    print("=" * 60)
    print("  TRAIN WITH au_continuous DATA")
    print("=" * 60)

    df_30m = load_30m_data()
    if df_30m.empty:
        print("No au_continuous 30m data found!")
        return

    # 生成特征（含微观特征，symbol=au_continuous）
    fe = FeatureEngineer(include_micro=True, micro_symbol='au_continuous')
    df_feat = fe.generate_features(df_30m.copy())

    # 目标: log(close_{t+1} / close_t)
    df_feat['target'] = np.log(df_feat['close'].shift(-1) / df_feat['close'])
    df_feat = df_feat.dropna()

    y = df_feat['target']
    drop_cols = [c for c in NON_FEATURE_COLS + ['target'] if c in df_feat.columns]
    X = df_feat.drop(columns=drop_cols).select_dtypes(include=[np.number])

    # 70/30 时间序列分割
    split = int(len(X) * 0.7)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}, Features: {X_train.shape[1]}")

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

    # 预测 & 评估
    y_pred = model.predict(X_test)
    mse = np.mean((y_test.values - y_pred) ** 2)
    rmse = np.sqrt(mse)
    corr = np.corrcoef(y_test.values, y_pred)[0, 1]
    direction_acc = np.mean((y_test.values > 0) == (y_pred > 0))

    print(f"\n{'='*60}")
    print(f"  RESULTS: au_continuous model")
    print(f"{'='*60}")
    print(f"  MSE:            {mse:.8f}")
    print(f"  RMSE:           {rmse:.6f}")
    print(f"  Correlation:    {corr:.4f}")
    print(f"  Direction Acc:  {direction_acc:.4f} ({direction_acc*100:.1f}%)")
    print(f"  Pred mean:      {y_pred.mean():.6f}")
    print(f"  Pred std:       {y_pred.std():.6f}")
    print(f"  Actual mean:    {y_test.mean():.6f}")
    print(f"  Actual std:     {y_test.std():.6f}")

    # 特征重要性 top 15
    importance = model.feature_importance(importance_type='gain')
    feat_imp = sorted(zip(X_train.columns, importance), key=lambda x: -x[1])
    print(f"\n  Top 15 features:")
    for i, (name, imp) in enumerate(feat_imp[:15]):
        print(f"    {i+1:2d}. {name:<30s} {imp:.1f}")

    # 保存模型
    model_path = "E:/quant-trading-mvp/models/lgbm_model_continuous.txt"
    model.save_model(model_path)
    print(f"\nModel saved to: {model_path}")


if __name__ == "__main__":
    main()
