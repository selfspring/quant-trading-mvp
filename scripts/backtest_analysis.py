"""
回测深入分析：多参数对比
- 不同置信度阈值
- 不同数据集（au_main vs au2606）
- 训练集/验证集分割
"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

import logging
import numpy as np
import pandas as pd
import vectorbt as vbt

from quant.common.config import config
from quant.common.db import db_engine
from quant.signal_generator.feature_engineer import FeatureEngineer
from quant.signal_generator.ml_predictor import MLPredictor

logging.basicConfig(level=logging.WARNING, force=True)


def load_data(symbol, interval):
    sql = """
        SELECT time AS timestamp, open, high, low, close, volume, open_interest
        FROM kline_data
        WHERE symbol = %(symbol)s AND interval = %(interval)s
        ORDER BY time
    """
    with db_engine(config) as engine:
        df = pd.read_sql(sql, engine, params={"symbol": symbol, "interval": interval})
    return df


def run_backtest(df, conf_threshold, label=""):
    fe = FeatureEngineer()
    ml = MLPredictor()

    features_df = fe.generate_features(df.copy())
    predict_cols = [c for c in features_df.columns if c not in ['timestamp', 'datetime', 'symbol', 'id', 'duration']]
    X = features_df[predict_cols]
    predictions = ml.model.predict(X)

    threshold = 0.005
    abs_pred = np.abs(predictions)
    confidence = np.where(
        abs_pred <= threshold, 0.0,
        np.where(abs_pred <= 0.02, 0.4 + (abs_pred - threshold) / (0.02 - threshold) * 0.5,
            np.where(abs_pred <= 0.05, 0.9 - (abs_pred - 0.02) / 0.03 * 0.4,
                np.maximum(0.3 - (abs_pred - 0.05) * 2, 0.1))))

    buy = (predictions > threshold) & (confidence >= conf_threshold)
    sell = (predictions < -threshold) & (confidence >= conf_threshold)

    entries = pd.Series(False, index=df.index)
    exits = pd.Series(False, index=df.index)
    entries.iloc[features_df.index] = buy
    exits.iloc[features_df.index] = sell

    close = df["close"]
    fees = 10.0 / close.mean()

    pf = vbt.Portfolio.from_signals(close, entries=entries, exits=exits,
                                     fees=fees, freq="30min", init_cash=100000)

    stats = pf.stats()
    trades = pf.trades.records_readable
    n_trades = len(trades)

    if n_trades > 0:
        profits = trades.loc[trades["PnL"] > 0, "PnL"]
        losses = trades.loc[trades["PnL"] < 0, "PnL"]
        avg_profit = profits.mean() if len(profits) > 0 else 0
        avg_loss = abs(losses.mean()) if len(losses) > 0 else 1
        pl_ratio = avg_profit / avg_loss if avg_loss > 0 else float("inf")
    else:
        pl_ratio = 0

    return {
        "label": label,
        "conf": conf_threshold,
        "trades": n_trades,
        "return": stats.get("Total Return [%]", 0),
        "sharpe": stats.get("Sharpe Ratio", 0),
        "max_dd": stats.get("Max Drawdown [%]", 0),
        "win_rate": stats.get("Win Rate [%]", 0),
        "pl_ratio": pl_ratio,
        "buy_signals": int(entries.sum()),
        "sell_signals": int(exits.sum()),
    }


def main():
    print("=" * 80)
    print("  BACKTEST DEEP ANALYSIS")
    print("=" * 80)

    # 1. 加载数据
    print("\n[1] Loading data...")
    au_main_30m = load_data("au_main", "30m")
    au2606_30m = load_data("au2606", "30m")
    print(f"  au_main 30m: {len(au_main_30m)} bars ({au_main_30m['timestamp'].min()} ~ {au_main_30m['timestamp'].max()})")
    print(f"  au2606 30m:  {len(au2606_30m)} bars ({au2606_30m['timestamp'].min()} ~ {au2606_30m['timestamp'].max()})")

    # 2. 多置信度阈值对比（au_main 30m）
    print("\n[2] Confidence threshold sweep (au_main 30m, full dataset)")
    print("-" * 80)
    print(f"{'Conf':>6} {'Trades':>7} {'Return%':>9} {'Sharpe':>8} {'MaxDD%':>8} {'WinRate%':>9} {'P/L':>6} {'BuySig':>7} {'SellSig':>8}")
    print("-" * 80)

    thresholds = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65]
    results = []
    for t in thresholds:
        r = run_backtest(au_main_30m, t, f"au_main_conf{t}")
        results.append(r)
        print(f"{r['conf']:>6.2f} {r['trades']:>7} {r['return']:>9.2f} {r['sharpe']:>8.4f} {r['max_dd']:>8.2f} {r['win_rate']:>9.2f} {r['pl_ratio']:>6.2f} {r['buy_signals']:>7} {r['sell_signals']:>8}")

    # 3. 样本外测试（训练集/验证集分割）
    print("\n[3] Out-of-sample test (au_main 30m)")
    split_idx = int(len(au_main_30m) * 0.7)
    train_df = au_main_30m.iloc[:split_idx].reset_index(drop=True)
    test_df = au_main_30m.iloc[split_idx:].reset_index(drop=True)
    print(f"  Train: {len(train_df)} bars ({train_df['timestamp'].min()} ~ {train_df['timestamp'].max()})")
    print(f"  Test:  {len(test_df)} bars ({test_df['timestamp'].min()} ~ {test_df['timestamp'].max()})")

    best_conf = 0.35  # 默认
    best_sharpe = -999
    for r in results:
        if r['sharpe'] > best_sharpe and r['trades'] >= 5:
            best_sharpe = r['sharpe']
            best_conf = r['conf']
    print(f"  Best conf from full sweep: {best_conf} (Sharpe={best_sharpe:.4f})")

    print(f"\n  Train set (conf={best_conf}):")
    r_train = run_backtest(train_df, best_conf, "train")
    print(f"    Return={r_train['return']:.2f}%, Sharpe={r_train['sharpe']:.4f}, MaxDD={r_train['max_dd']:.2f}%, Trades={r_train['trades']}, WinRate={r_train['win_rate']:.2f}%")

    print(f"\n  Test set (conf={best_conf}):")
    r_test = run_backtest(test_df, best_conf, "test")
    print(f"    Return={r_test['return']:.2f}%, Sharpe={r_test['sharpe']:.4f}, MaxDD={r_test['max_dd']:.2f}%, Trades={r_test['trades']}, WinRate={r_test['win_rate']:.2f}%")

    # 4. au2606 单独回测
    if len(au2606_30m) >= 100:
        print(f"\n[4] au2606 30m backtest (conf={best_conf})")
        r_2606 = run_backtest(au2606_30m, best_conf, "au2606")
        print(f"    Return={r_2606['return']:.2f}%, Sharpe={r_2606['sharpe']:.4f}, MaxDD={r_2606['max_dd']:.2f}%, Trades={r_2606['trades']}, WinRate={r_2606['win_rate']:.2f}%")

    # 5. 信号分布分析
    print("\n[5] Signal distribution (au_main 30m)")
    fe = FeatureEngineer()
    ml = MLPredictor()
    features_df = fe.generate_features(au_main_30m.copy())
    predict_cols = [c for c in features_df.columns if c not in ['timestamp', 'datetime', 'symbol', 'id', 'duration']]
    predictions = ml.model.predict(features_df[predict_cols])
    abs_pred = np.abs(predictions)
    confidence = np.where(
        abs_pred <= 0.005, 0.0,
        np.where(abs_pred <= 0.02, 0.4 + (abs_pred - 0.005) / 0.015 * 0.5,
            np.where(abs_pred <= 0.05, 0.9 - (abs_pred - 0.02) / 0.03 * 0.4,
                np.maximum(0.3 - (abs_pred - 0.05) * 2, 0.1))))

    print(f"  Predictions: mean={predictions.mean():.6f}, std={predictions.std():.6f}")
    print(f"  Predictions: min={predictions.min():.6f}, max={predictions.max():.6f}")
    print(f"  Confidence:  mean={confidence.mean():.4f}, std={confidence.std():.4f}")
    print(f"  Confidence distribution:")
    for lo, hi in [(0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]:
        cnt = ((confidence >= lo) & (confidence < hi)).sum()
        pct = cnt / len(confidence) * 100
        print(f"    [{lo:.1f}, {hi:.1f}): {cnt:>6} ({pct:>5.1f}%)")

    # 6. 结论
    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    print(f"  Best confidence threshold: {best_conf}")
    print(f"  Full dataset:  Sharpe={best_sharpe:.4f}")
    print(f"  Train set:     Sharpe={r_train['sharpe']:.4f}, Trades={r_train['trades']}")
    print(f"  Test set:      Sharpe={r_test['sharpe']:.4f}, Trades={r_test['trades']}")
    if r_test['sharpe'] > 0 and r_test['trades'] >= 3:
        print("  --> Out-of-sample positive: strategy has some predictive power")
    else:
        print("  --> Out-of-sample weak/negative: possible overfitting")
    print("=" * 80)


if __name__ == "__main__":
    main()
