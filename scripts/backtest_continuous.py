"""回测对比：旧模型 vs 新连续合约模型"""
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


def load_data(symbol, interval):
    sql = (
        "SELECT time AS timestamp, open, high, low, close, volume, open_interest "
        "FROM kline_data "
        f"WHERE symbol='{symbol}' AND interval='{interval}' "
        "ORDER BY time"
    )
    with db_engine(config) as engine:
        df = pd.read_sql(sql, engine)
    return df


def run_backtest(model_path, df_30m, fe, label):
    """用指定模型对 30m 数据做回测"""
    model = lgb.Booster(model_file=model_path)

    df_feat = fe.generate_features(df_30m.copy())
    drop_cols = [c for c in NON_FEATURE_COLS if c in df_feat.columns]
    X = df_feat.drop(columns=drop_cols).select_dtypes(include=[np.number])

    # 预测
    preds = model.predict(X)

    # 信号
    threshold = 0.005
    abs_pred = np.abs(preds)
    confidence = np.where(
        abs_pred <= threshold, 0.0,
        np.where(abs_pred <= 0.02,
                 0.4 + (abs_pred - threshold) / (0.02 - threshold) * 0.5,
                 np.where(abs_pred <= 0.05,
                          0.9 - (abs_pred - 0.02) / 0.03 * 0.4,
                          np.maximum(0.3 - (abs_pred - 0.05) * 2, 0.1))))

    conf_threshold = config.ml.confidence_threshold
    buy = (preds > threshold) & (confidence >= conf_threshold)
    sell = (preds < -threshold) & (confidence >= conf_threshold)

    # 简单回测：按信号持仓，计算收益
    close = df_feat['close'].values
    position = np.zeros(len(close))
    for i in range(len(close)):
        if buy[i]:
            position[i] = 1
        elif sell[i]:
            position[i] = -1
        elif i > 0:
            position[i] = position[i-1]

    # 收益计算
    returns = np.diff(close) / close[:-1]
    strategy_returns = position[:-1] * returns

    total_return = (1 + strategy_returns).prod() - 1
    sharpe = np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-10) * np.sqrt(252 * 8)
    max_dd = np.min(np.minimum.accumulate((1 + strategy_returns).cumprod()) / 
                    np.maximum.accumulate((1 + strategy_returns).cumprod()) - 1)
    n_trades = np.sum(np.diff(position) != 0)
    win_rate = np.mean(strategy_returns[strategy_returns != 0] > 0) if np.any(strategy_returns != 0) else 0

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Total Return:    {total_return*100:.2f}%")
    print(f"  Sharpe Ratio:    {sharpe:.4f}")
    print(f"  Max Drawdown:    {max_dd*100:.2f}%")
    print(f"  Trades:          {n_trades}")
    print(f"  Win Rate:        {win_rate*100:.1f}%")
    print(f"  Pred mean:       {preds.mean():.6f}")
    print(f"  Pred std:        {preds.std():.6f}")
    print(f"  Buy signals:     {buy.sum()}")
    print(f"  Sell signals:    {sell.sum()}")

    return {
        'total_return': total_return, 'sharpe': sharpe,
        'max_dd': max_dd, 'n_trades': n_trades, 'win_rate': win_rate,
    }


def main():
    print("=" * 60)
    print("  BACKTEST COMPARISON: Old vs Continuous Model")
    print("=" * 60)

    # 加载 au_continuous 30m 数据
    df_30m = load_data('au_continuous', '30m')
    print(f"Loaded {len(df_30m)} au_continuous 30m bars")

    # 旧模型（无微观特征）
    fe_old = FeatureEngineer(include_micro=False)
    old_metrics = run_backtest(
        'E:/quant-trading-mvp/models/lgbm_model.txt',
        df_30m, fe_old, "OLD MODEL (lgbm_model.txt, no micro)")

    # 新模型（含微观特征，au_continuous）
    fe_new = FeatureEngineer(include_micro=True, micro_symbol='au_continuous')
    new_metrics = run_backtest(
        'E:/quant-trading-mvp/models/lgbm_model_continuous.txt',
        df_30m, fe_new, "NEW MODEL (lgbm_model_continuous.txt, with micro)")

    # 对比
    print(f"\n{'='*60}")
    print(f"  COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"  {'Metric':<20s} {'Old':>12s} {'New':>12s}")
    print(f"  {'-'*44}")
    print(f"  {'Return':<20s} {old_metrics['total_return']*100:>11.2f}% {new_metrics['total_return']*100:>11.2f}%")
    print(f"  {'Sharpe':<20s} {old_metrics['sharpe']:>12.4f} {new_metrics['sharpe']:>12.4f}")
    print(f"  {'Max DD':<20s} {old_metrics['max_dd']*100:>11.2f}% {new_metrics['max_dd']*100:>11.2f}%")
    print(f"  {'Trades':<20s} {old_metrics['n_trades']:>12.0f} {new_metrics['n_trades']:>12.0f}")
    print(f"  {'Win Rate':<20s} {old_metrics['win_rate']*100:>11.1f}% {new_metrics['win_rate']*100:>11.1f}%")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
