"""
因子评估器：自动计算 IC/IR/换手率/单调性
"""
import numpy as np
import pandas as pd
from scipy import stats


def calc_ic_series(factor: pd.Series, forward_return: pd.Series, method='rank') -> pd.Series:
    """逐期计算 IC（信息系数）"""
    if method == 'rank':
        return factor.rolling(20).corr(forward_return)
    return factor.rolling(20).corr(forward_return)


def evaluate_factor(factor_values: pd.Series, forward_return: pd.Series, name: str = '') -> dict:
    """
    评估单个因子
    
    Args:
        factor_values: 因子值序列
        forward_return: 未来收益率序列（与因子对齐）
        name: 因子名称
    
    Returns:
        dict: 评估指标
    """
    # 去掉 NaN
    valid = ~(factor_values.isna() | forward_return.isna() | np.isinf(factor_values) | np.isinf(forward_return))
    f = factor_values[valid]
    r = forward_return[valid]
    
    if len(f) < 100:
        return {'name': name, 'valid': False, 'reason': f'too few samples ({len(f)})'}
    
    # 1. IC（Rank IC）
    rank_ic = stats.spearmanr(f, r)[0]
    
    # 2. IC 序列（滚动20期）
    ic_series = f.rolling(20).corr(r).dropna()
    ic_mean = ic_series.mean()
    ic_std = ic_series.std()
    ir = ic_mean / ic_std if ic_std > 0 else 0  # 信息比率
    
    # 3. IC 胜率（IC > 0 的比例）
    ic_win_rate = (ic_series > 0).mean()
    
    # 4. 换手率（因子值变化频率）
    turnover = f.diff().abs().mean() / f.abs().mean() if f.abs().mean() > 0 else 0
    
    # 5. 分组单调性（5组）
    try:
        groups = pd.qcut(f, 5, labels=False, duplicates='drop')
        group_returns = r.groupby(groups).mean()
        # 检查是否单调
        diffs = group_returns.diff().dropna()
        monotonic_score = diffs[diffs > 0].count() / len(diffs) if len(diffs) > 0 else 0
    except:
        monotonic_score = 0
        group_returns = pd.Series()
    
    # 6. 方向准确率
    direction_acc = np.mean(np.sign(f) == np.sign(r))
    
    # 7. 多空收益
    long_mask = f > f.quantile(0.8)
    short_mask = f < f.quantile(0.2)
    long_return = r[long_mask].mean() if long_mask.sum() > 10 else 0
    short_return = r[short_mask].mean() if short_mask.sum() > 10 else 0
    long_short_return = long_return - short_return
    
    return {
        'name': name,
        'valid': True,
        'samples': len(f),
        'rank_ic': round(rank_ic, 4),
        'ic_mean': round(ic_mean, 4),
        'ic_std': round(ic_std, 4),
        'ir': round(ir, 4),
        'ic_win_rate': round(ic_win_rate, 4),
        'direction_acc': round(direction_acc, 4),
        'turnover': round(turnover, 4),
        'monotonic_score': round(monotonic_score, 4),
        'long_short_return': round(long_short_return, 6),
        'long_return': round(long_return, 6),
        'short_return': round(short_return, 6),
    }


def evaluate_all_factors(factors_df: pd.DataFrame, forward_return: pd.Series) -> pd.DataFrame:
    """批量评估所有因子"""
    results = []
    for col in factors_df.columns:
        r = evaluate_factor(factors_df[col], forward_return, name=col)
        results.append(r)
    
    df = pd.DataFrame(results)
    if 'rank_ic' in df.columns:
        df['abs_ic'] = df['rank_ic'].abs()
        df = df.sort_values('abs_ic', ascending=False)
    return df


def print_factor_report(eval_df: pd.DataFrame, top_n: int = 20):
    """打印因子评估报告"""
    valid = eval_df[eval_df['valid'] == True]
    invalid = eval_df[eval_df['valid'] == False]
    
    print(f"\nTotal factors: {len(eval_df)}, Valid: {len(valid)}, Invalid: {len(invalid)}")
    
    if len(valid) == 0:
        print("No valid factors!")
        return
    
    # 按 |IC| 排序
    top = valid.head(top_n)
    
    print(f"\nTop {min(top_n, len(top))} factors by |Rank IC|:")
    print("-" * 100)
    print(f"{'Factor':<25} {'RankIC':>8} {'IC_mean':>8} {'IR':>8} {'IC_win%':>8} {'Dir_acc':>8} {'L/S_ret':>10} {'Mono':>6}")
    print("-" * 100)
    
    for _, row in top.iterrows():
        print(f"{row['name']:<25} {row['rank_ic']:>8.4f} {row['ic_mean']:>8.4f} {row['ir']:>8.4f} "
              f"{row['ic_win_rate']:>8.4f} {row['direction_acc']:>8.4f} {row['long_short_return']:>10.6f} "
              f"{row['monotonic_score']:>6.2f}")
    
    # 统计
    print(f"\nFactors with |IC| > 0.03: {(valid['abs_ic'] > 0.03).sum()}")
    print(f"Factors with |IC| > 0.05: {(valid['abs_ic'] > 0.05).sum()}")
    print(f"Factors with IR > 0.3: {(valid['ir'].abs() > 0.3).sum()}")
