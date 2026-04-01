"""用 au_main 30m + 多合约 1m 微观特征训练"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

import logging
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_squared_error
from sqlalchemy import text

from quant.common.config import config
from quant.common.db import db_engine
from quant.signal_generator.feature_engineer import FeatureEngineer

logging.basicConfig(level=logging.WARNING, force=True)


def main():
    # 1. 读 au_main 30m
    with db_engine(config) as engine:
        df = pd.read_sql(text(
            "SELECT time as timestamp, open, high, low, close, volume, open_interest "
            "FROM kline_data WHERE symbol='au_main' AND interval='30m' ORDER BY time"
        ), engine)
    print(f"au_main 30m: {len(df)} rows")

    # 2. 生成特征（含微观 vs 不含）
    fe_micro = FeatureEngineer(include_micro=True)
    features_micro = fe_micro.generate_features(df.copy())

    fe_base = FeatureEngineer(include_micro=False)
    features_base = fe_base.generate_features(df.copy())

    # 3. 目标变量 & 训练
    exclude_cols = ['timestamp', 'datetime', 'symbol', 'id', 'duration']

    for label, features_df in [("baseline(47)", features_base), ("micro(57)", features_micro)]:
        pred_cols = [c for c in features_df.columns if c not in exclude_cols]
        X = features_df[pred_cols]

        # 目标：下一根 K 线收益率
        close = df.loc[features_df.index, 'close'].values
        target = np.log(close[1:] / close[:-1])
        X = X.iloc[:-1]

        # 去掉 target 中的 NaN
        valid = ~np.isnan(target)
        X = X.loc[valid]
        target = target[valid]

        # 70/30 分割
        split = int(len(X) * 0.7)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = target[:split], target[split:]

        # 训练
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

        model = lgb.train(
            params, train_data, num_boost_round=500,
            valid_sets=[valid_data],
            callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
        )

        preds = model.predict(X_test)
        mse = mean_squared_error(y_test, preds)
        corr = np.corrcoef(y_test, preds)[0, 1] if np.std(preds) > 0 else 0
        direction = np.mean(np.sign(preds) == np.sign(y_test))

        print(f"\n=== {label} ===")
        print(f"Features: {len(pred_cols)}")
        print(f"Train: {len(X_train)}, Test: {len(X_test)}")
        print(f"MSE: {mse:.8f}, RMSE: {np.sqrt(mse):.6f}")
        print(f"Correlation: {corr:.4f}")
        print(f"Direction accuracy: {direction:.4f}")
        print(f"Pred mean: {preds.mean():.6f}, std: {preds.std():.6f}")
        print(f"Actual mean: {y_test.mean():.6f}, std: {y_test.std():.6f}")

        # 微观特征重要度
        if 'micro' in label:
            importance = dict(zip(pred_cols, model.feature_importance()))
            micro_feats = {k: v for k, v in importance.items() if k.startswith('micro_')}
            print(f"\nMicro feature importance:")
            for k, v in sorted(micro_feats.items(), key=lambda x: -x[1]):
                print(f"  {k}: {v}")

            # 保存模型
            import os
            os.makedirs('models', exist_ok=True)
            model.save_model('models/lgbm_model_v2.txt')
            print(f"\nModel saved to models/lgbm_model_v2.txt")

            # 信号统计
            threshold = 0.005
            buy = (preds > threshold).sum()
            sell = (preds < -threshold).sum()
            neutral = len(preds) - buy - sell
            print(f"Signals (threshold={threshold}): buy={buy}, sell={sell}, neutral={neutral}")


if __name__ == '__main__':
    main()
