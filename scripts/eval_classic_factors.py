"""
经典因子评估：计算所有因子的 IC/IR，找出有效因子
"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')

import logging
import numpy as np
import pandas as pd

from quant.common.config import config
from quant.common.db import db_engine
from quant.factors.classic_factors import CLASSIC_FACTORS, compute_all_factors
from quant.factors.factor_evaluator import evaluate_all_factors, print_factor_report

logging.basicConfig(level=logging.WARNING, force=True)


def main():
    print("=" * 70)
    print("  CLASSIC FACTOR EVALUATION")
    print("=" * 70)

    # 加载数据
    with db_engine(config) as engine:
        df = pd.read_sql("""
            SELECT time as timestamp, open, high, low, close, volume, open_interest
            FROM kline_data WHERE symbol='au_main' AND interval='30m'
            ORDER BY time
        """, engine)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"Data: {len(df)} bars ({df.timestamp.min()} ~ {df.timestamp.max()})")

    # 计算所有因子
    print(f"\nComputing {len(CLASSIC_FACTORS)} classic factors...")
    factors = compute_all_factors(df)
    print(f"Computed. Shape: {factors.shape}")

    # 计算未来收益率（多个 horizon）
    for horizon, label in [(4, '2h'), (8, '4h'), (16, '8h')]:
        print(f"\n{'='*70}")
        print(f"  HORIZON = {label} ({horizon} bars)")
        print(f"{'='*70}")

        forward_return = np.log(df['close'].shift(-horizon) / df['close'])
        eval_df = evaluate_all_factors(factors, forward_return)
        print_factor_report(eval_df, top_n=20)

        # 保存结果
        eval_df.to_csv(f'E:/quant-trading-mvp/data/factor_eval_{label}.csv', index=False)

    # 汇总：哪些因子在多个 horizon 上都有效
    print(f"\n{'='*70}")
    print("  CROSS-HORIZON SUMMARY")
    print(f"{'='*70}")

    all_evals = {}
    for horizon, label in [(4, '2h'), (8, '4h'), (16, '8h')]:
        ev = pd.read_csv(f'E:/quant-trading-mvp/data/factor_eval_{label}.csv')
        ev = ev[ev['valid'] == True]
        all_evals[label] = ev.set_index('name')['rank_ic']

    combined = pd.DataFrame(all_evals)
    combined['avg_abs_ic'] = combined.abs().mean(axis=1)
    combined['consistent'] = (combined[['2h', '4h', '8h']].apply(lambda x: np.sign(x), axis=0).nunique(axis=1) == 1)
    combined = combined.sort_values('avg_abs_ic', ascending=False)

    print(f"\nTop 15 factors (avg |IC| across horizons):")
    print("-" * 80)
    print(f"{'Factor':<25} {'2h':>8} {'4h':>8} {'8h':>8} {'Avg|IC|':>8} {'Consistent':>10}")
    print("-" * 80)
    for name, row in combined.head(15).iterrows():
        print(f"{name:<25} {row['2h']:>8.4f} {row['4h']:>8.4f} {row['8h']:>8.4f} "
              f"{row['avg_abs_ic']:>8.4f} {'YES' if row['consistent'] else 'no':>10}")

    # 有效因子列表
    effective = combined[(combined['avg_abs_ic'] > 0.02) & combined['consistent']]
    print(f"\nEffective factors (avg|IC|>0.02 & consistent direction): {len(effective)}")
    for name in effective.index:
        print(f"  {name}")


if __name__ == '__main__':
    main()
