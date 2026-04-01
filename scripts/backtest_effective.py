"""
用有效因子模型跑 VectorBT 回测
"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

import logging
import numpy as np
import pandas as pd
import lightgbm as lgb
import vectorbt as vbt

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
    print("  BACKTEST: EFFECTIVE FACTOR MODEL")
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

    # 计算因子
    factors = pd.DataFrame(index=df.index)
    for name in EFFECTIVE_FACTORS:
        factors[name] = CLASSIC_FACTORS[name](df)

    # 加载模型
    model = lgb.Booster(model_file='models/lgbm_model_v2.txt')
    print(f"Model loaded: {model.num_trees()} trees")

    # 预测
    valid = ~factors.isna().any(axis=1)
    preds = np.full(len(df), np.nan)
    preds[valid] = model.predict(factors[valid])

    pred_std = np.nanstd(preds)
    pred_mean = np.nanmean(preds)
    print(f"Predictions: mean={pred_mean:.6f}, std={pred_std:.6f}")

    # 多阈值回测
    close = df['close']
    fees = 10.0 / close.mean()  # 单边手续费

    print(f"\nFees: {fees:.6f} ({10.0/close.mean()*100:.4f}%)")
    print(f"\n{'Threshold':>12} {'Trades':>7} {'Return%':>9} {'Sharpe':>8} {'MaxDD%':>8} {'WinRate%':>9} {'P/L':>8}")
    print("-" * 75)

    for mult in [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]:
        threshold = pred_std * mult

        entries = pd.Series(False, index=df.index)
        exits = pd.Series(False, index=df.index)

        buy_mask = preds > threshold
        sell_mask = preds < -threshold

        entries[buy_mask] = True
        exits[sell_mask] = True

        pf = vbt.Portfolio.from_signals(
            close, entries=entries, exits=exits,
            fees=fees, freq="30min", init_cash=100000
        )

        stats = pf.stats()
        trades = pf.trades.records_readable
        n_trades = len(trades)

        if n_trades > 0:
            profits = trades.loc[trades["PnL"] > 0, "PnL"]
            losses = trades.loc[trades["PnL"] < 0, "PnL"]
            avg_profit = profits.mean() if len(profits) > 0 else 0
            avg_loss = abs(losses.mean()) if len(losses) > 0 else 1
            pl_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
            win_rate = stats.get("Win Rate [%]", 0)
        else:
            pl_ratio = 0
            win_rate = 0

        ret = stats.get("Total Return [%]", 0)
        sharpe = stats.get("Sharpe Ratio", 0)
        maxdd = stats.get("Max Drawdown [%]", 0)

        print(f"{mult:>10.1f}x std {n_trades:>7} {ret:>9.2f} {sharpe:>8.4f} {maxdd:>8.2f} {win_rate:>9.2f} {pl_ratio:>8.2f}")

    # 样本外测试（70/30 分割）
    print(f"\n{'='*70}")
    print("  OUT-OF-SAMPLE TEST (last 30%)")
    print(f"{'='*70}")

    split = int(len(df) * 0.7)
    oos_close = close.iloc[split:].reset_index(drop=True)
    oos_preds = preds[split:]

    oos_pred_std = np.nanstd(oos_preds)

    for mult in [0.5, 1.0, 1.5]:
        threshold = oos_pred_std * mult

        entries = pd.Series(False, index=oos_close.index)
        exits = pd.Series(False, index=oos_close.index)

        buy_mask = oos_preds > threshold
        sell_mask = oos_preds < -threshold

        # 对齐索引
        valid_idx = np.arange(len(oos_close))
        entries.iloc[buy_mask[~np.isnan(oos_preds)]] = True
        exits.iloc[sell_mask[~np.isnan(oos_preds)]] = True

        oos_fees = 10.0 / oos_close.mean()
        pf = vbt.Portfolio.from_signals(
            oos_close, entries=entries, exits=exits,
            fees=oos_fees, freq="30min", init_cash=100000
        )

        stats = pf.stats()
        n_trades = len(pf.trades.records_readable)
        ret = stats.get("Total Return [%]", 0)
        sharpe = stats.get("Sharpe Ratio", 0)
        maxdd = stats.get("Max Drawdown [%]", 0)
        win_rate = stats.get("Win Rate [%]", 0)

        print(f"  {mult:.1f}x std: trades={n_trades}, return={ret:.2f}%, sharpe={sharpe:.4f}, maxdd={maxdd:.2f}%, winrate={win_rate:.2f}%")


if __name__ == '__main__':
    main()
