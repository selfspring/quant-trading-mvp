"""
用因子评估筛选出的11个有效因子训练回归模型
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
from quant.factors.classic_factors import CLASSIC_FACTORS

logging.basicConfig(level=logging.WARNING, force=True)

EFFECTIVE_FACTORS = [
    'bb_width', 'oi_concentration', 'oi_change_rate', 'trend_strength',
    'volume_price_corr', 'rsi_14', 'ma_cross_5_20', 'macd_hist',
    'money_flow', 'oi_price_divergence', 'momentum_60',
]


def main():
    print("=" * 70)
    print("  EFFECTIVE FACTOR REGRESSION MODEL")
    print("=" * 70)

    # 加载数据
    with db_engine(config) as engine:
        df = pd.read_sql("""
            SELECT time as timestamp, open, high, low, close, volume, open_interest
            FROM kline_data WHERE symbol='au_main' AND interval='30m'
            ORDER BY time
        """, engine)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"Data: {len(df)} bars")

    # 计算有效因子
    factors = pd.DataFrame(index=df.index)
    for name in EFFECTIVE_FACTORS:
        factors[name] = CLASSIC_FACTORS[name](df)
    print(f"Factors: {len(EFFECTIVE_FACTORS)}")

    # 多 horizon 训练
    for horizon in [4, 8, 16]:
        label = f"{horizon * 30 // 60}h"
        print(f"\n{'='*70}")
        print(f"  HORIZON = {label} ({horizon} bars)")
        print(f"{'='*70}")

        target = np.log(df['close'].shift(-horizon) / df['close'])
        X = factors.copy()

        # 去 NaN
        valid = ~(X.isna().any(axis=1) | target.isna())
        X = X[valid]
        target = target[valid].values

        split = int(len(X) * 0.7)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = target[:split], target[split:]

        print(f"  Train: {len(X_train)}, Test: {len(X_test)}")

        # 训练多组参数
        configs = [
            ('conservative', {'num_leaves': 15, 'learning_rate': 0.03, 'min_data_in_leaf': 50,
                              'lambda_l1': 0.5, 'lambda_l2': 0.5, 'feature_fraction': 0.8,
                              'bagging_fraction': 0.8, 'bagging_freq': 5}),
            ('moderate', {'num_leaves': 31, 'learning_rate': 0.05, 'min_data_in_leaf': 30,
                          'lambda_l1': 0.1, 'lambda_l2': 0.1, 'feature_fraction': 0.8,
                          'bagging_fraction': 0.8, 'bagging_freq': 5}),
            ('aggressive', {'num_leaves': 63, 'learning_rate': 0.1, 'min_data_in_leaf': 10,
                            'lambda_l1': 0.01, 'lambda_l2': 0.01, 'feature_fraction': 0.9,
                            'bagging_fraction': 0.9, 'bagging_freq': 3}),
        ]

        best_model = None
        best_corr = -999
        best_label = ''

        for cfg_name, params in configs:
            params['objective'] = 'regression'
            params['metric'] = 'mse'
            params['verbose'] = -1

            train_data = lgb.Dataset(X_train, label=y_train)
            valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

            model = lgb.train(params, train_data, num_boost_round=1000,
                              valid_sets=[valid_data],
                              callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)])

            preds = model.predict(X_test)
            mse = mean_squared_error(y_test, preds)
            corr = np.corrcoef(y_test, preds)[0, 1] if np.std(preds) > 1e-10 else 0
            direction = np.mean(np.sign(preds) == np.sign(y_test))

            # 信号统计
            pred_std = preds.std()
            threshold = pred_std * 1.0  # 1倍标准差作为阈值
            buy = (preds > threshold).sum()
            sell = (preds < -threshold).sum()

            print(f"\n  [{cfg_name}] iter={model.best_iteration}")
            print(f"    MSE={mse:.8f} Corr={corr:.4f} Dir={direction:.4f}")
            print(f"    Pred: mean={preds.mean():.6f} std={pred_std:.6f}")
            print(f"    Signals (>{threshold:.6f}): buy={buy} sell={sell} total={buy+sell}")

            if corr > best_corr:
                best_corr = corr
                best_model = model
                best_label = cfg_name

        print(f"\n  Best config: {best_label} (corr={best_corr:.4f})")

        # 保存最佳 horizon=8 模型
        if horizon == 8 and best_model:
            best_model.save_model('models/lgbm_model_v2.txt')
            print(f"  Saved to models/lgbm_model_v2.txt")

            # 特征重要度
            importance = sorted(zip(EFFECTIVE_FACTORS, best_model.feature_importance()),
                                key=lambda x: -x[1])
            print(f"  Feature importance:")
            for name, imp in importance:
                print(f"    {name}: {imp}")

    print(f"\n{'='*70}")
    print("  DONE")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
