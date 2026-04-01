import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
import numpy as np
import pandas as pd
from quant.common.config import config
from quant.common.db import db_engine
from quant.factors.factor_evaluator import evaluate_factor
import json
from datetime import datetime

with db_engine(config) as engine:
    df = pd.read_sql("""
        SELECT time as timestamp, open, high, low, close, volume, open_interest
        FROM kline_data WHERE symbol='au_main' AND interval='30m'
        ORDER BY time
    """, engine)
df['timestamp'] = pd.to_datetime(df['timestamp'])

def test_factor(name, desc, source, factor_values):
    results = {}
    for h in [4, 8, 16]:
        fwd = np.log(df['close'].shift(-h) / df['close'])
        r = evaluate_factor(factor_values, fwd, name=name)
        results[f'{h*30//60}h'] = r
        ric = r.get('rank_ic', 0)
        ir = r.get('ir', 0)
        da = r.get('direction_acc', 0)
        print(f"  {h*30//60}h: IC={ric:.4f}, IR={ir:.4f}, Dir={da:.4f}")
    avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results])
    record = {
        'timestamp': datetime.now().isoformat(),
        'name': name,
        'description': desc,
        'source': source,
        'avg_abs_ic': round(float(avg_ic), 4),
        'results': {k: {kk: (float(vv) if isinstance(vv, (np.floating, np.integer)) else vv) for kk, vv in v.items() if kk != 'valid'} for k, v in results.items()},
        'effective': bool(avg_ic > 0.02),
    }
    with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    tag = "** EFFECTIVE **" if avg_ic > 0.02 else ""
    print(f"{name} Avg |IC|: {avg_ic:.4f} {tag}")
    print("---")
    return avg_ic > 0.02

# ============================================================
# Factor 1: OI Herfindahl Concentration
# OI变化的集中度指数 - 大资金集中进出的信号
# ============================================================
print("=== Factor 1: oi_herfindahl ===")
oi_chg = df['open_interest'].diff().abs()
sum_sq = oi_chg.rolling(20).apply(lambda x: (x**2).sum(), raw=True)
sq_sum = oi_chg.rolling(20).sum() ** 2
hhi = sum_sq / sq_sum.replace(0, np.nan)
price_dir = np.sign(df['close'].pct_change(5))
hhi_z = (hhi - hhi.rolling(60).mean()) / hhi.rolling(60).std().replace(0, np.nan)
f1 = hhi_z * price_dir
test_factor('oi_herfindahl',
    'OI变化Herfindahl集中度：OI变化平方和/总和平方的z-score乘以价格方向',
    'Herfindahl index applied to OI changes', f1)

# ============================================================
# Factor 2: Volume Impulse Response
# 放量脉冲后价格的持续性响应
# ============================================================
print("=== Factor 2: volume_impulse_response ===")
vol_z = (df['volume'] - df['volume'].rolling(20).mean()) / df['volume'].rolling(20).std().replace(0, np.nan)
ret = df['close'].pct_change()
impulse = (vol_z > 1.5).astype(float) * np.sign(ret)
response = impulse.rolling(10).sum()
response_z = (response - response.rolling(60).mean()) / response.rolling(60).std().replace(0, np.nan)
f2 = response_z
test_factor('volume_impulse_response',
    '成交量脉冲响应：放量K线收益方向的累积响应z-score',
    'impulse response function applied to volume spikes', f2)

# ============================================================
# Factor 3: OI Velocity Curvature Ratio
# OI一阶导/二阶导比值 - 趋势惯性
# ============================================================
print("=== Factor 3: oi_vel_curv_ratio ===")
oi = df['open_interest']
velocity = oi.diff(5) / 5
accel = velocity.diff(5) / 5
ratio = velocity / accel.replace(0, np.nan)
ratio = ratio.clip(-100, 100)
ratio_z = (ratio - ratio.rolling(60).mean()) / ratio.rolling(60).std().replace(0, np.nan)
price_mom = np.sign(df['close'].pct_change(10))
f3 = ratio_z * price_mom
test_factor('oi_vel_curv_ratio',
    'OI速度曲率比：OI一阶导与二阶导比值z-score乘以价格动量方向',
    'OI velocity to curvature ratio', f3)

# ============================================================
# Factor 4: Relative Range Position Momentum
# 多周期价格在振幅中位置的动量差
# ============================================================
print("=== Factor 4: range_pos_momentum ===")
def range_pos(w):
    h = df['high'].rolling(w).max()
    l = df['low'].rolling(w).min()
    return (df['close'] - l) / (h - l).replace(0, np.nan)
rp_short = range_pos(10)
rp_long = range_pos(40)
rp_diff = rp_short - rp_long
rp_z = (rp_diff - rp_diff.rolling(60).mean()) / rp_diff.rolling(60).std().replace(0, np.nan)
f4 = rp_z
test_factor('range_pos_momentum',
    '区间位置动量差：短期与长期价格在振幅中位置的差z-score',
    'multi-period range position momentum', f4)

# ============================================================
# Factor 5: OI Absorption Ratio
# OI吸收比：价格波动被OI变化吸收的程度
# ============================================================
print("=== Factor 5: oi_absorption_ratio ===")
price_var = df['close'].pct_change().abs().rolling(20).sum()
oi_var = df['open_interest'].pct_change().abs().rolling(20).sum()
absorption = oi_var / price_var.replace(0, np.nan)
abs_z = (absorption - absorption.rolling(60).mean()) / absorption.rolling(60).std().replace(0, np.nan)
mom_dir = np.sign(df['close'].pct_change(10))
f5 = abs_z * mom_dir
test_factor('oi_absorption_ratio',
    'OI吸收比：OI变化累积/价格变化累积的z-score乘以动量方向',
    'OI absorption of price volatility', f5)

# ============================================================
# Factor 6: Candle Entropy
# K线形态信息熵 - 形态多样性低=趋势明确
# ============================================================
print("=== Factor 6: candle_entropy ===")
body = (df['close'] - df['open']) / (df['high'] - df['low']).replace(0, np.nan)
body = body.clip(-1, 1)
# 离散化为5个bin
bins = pd.cut(body, bins=5, labels=False)
def rolling_entropy(s, w=30):
    result = pd.Series(np.nan, index=s.index)
    for i in range(w, len(s)):
        window = s.iloc[i-w:i].dropna()
        if len(window) < w * 0.5:
            continue
        counts = window.value_counts(normalize=True)
        ent = -(counts * np.log2(counts + 1e-10)).sum()
        result.iloc[i] = ent
    return result
# 用更快的方式
from collections import Counter
ent_vals = np.full(len(df), np.nan)
w = 30
bins_arr = bins.values
for i in range(w, len(df)):
    window = bins_arr[i-w:i]
    valid = window[~np.isnan(window)]
    if len(valid) < w * 0.5:
        continue
    counts = np.bincount(valid.astype(int), minlength=5)
    probs = counts / counts.sum()
    probs = probs[probs > 0]
    ent_vals[i] = -(probs * np.log2(probs)).sum()
candle_ent = pd.Series(ent_vals, index=df.index)
ent_z = (candle_ent - candle_ent.rolling(60).mean()) / candle_ent.rolling(60).std().replace(0, np.nan)
# 低熵=趋势明确，乘以动量方向
f6 = -ent_z * np.sign(df['close'].pct_change(10))
test_factor('candle_entropy',
    'K线形态熵取反：K线body ratio分布熵z-score取反乘以动量方向',
    'candle pattern entropy', f6)

# ============================================================
# Factor 7: OI Momentum Sharpe
# OI动量的夏普比 - OI变化的信噪比
# ============================================================
print("=== Factor 7: oi_momentum_sharpe ===")
oi_ret = df['open_interest'].pct_change()
oi_sharpe = oi_ret.rolling(20).mean() / oi_ret.rolling(20).std().replace(0, np.nan)
oi_sharpe_z = (oi_sharpe - oi_sharpe.rolling(60).mean()) / oi_sharpe.rolling(60).std().replace(0, np.nan)
f7 = oi_sharpe_z
test_factor('oi_momentum_sharpe',
    'OI动量夏普比：OI变化率均值/标准差的z-score',
    'OI momentum Sharpe ratio', f7)

# ============================================================
# Factor 8: Volume OI Granger Proxy
# 量仓因果代理：成交量领先OI变化的程度
# ============================================================
print("=== Factor 8: vol_oi_granger ===")
vol_lag = df['volume'].shift(1)
oi_chg_now = df['open_interest'].diff()
# 滚动相关：昨日成交量与今日OI变化
corr = vol_lag.rolling(20).corr(oi_chg_now)
corr_z = (corr - corr.rolling(60).mean()) / corr.rolling(60).std().replace(0, np.nan)
f8 = corr_z * np.sign(df['close'].pct_change(5))
test_factor('vol_oi_granger',
    '量仓Granger代理：滞后成交量与OI变化的滚动相关z乘以价格方向',
    'volume leading OI Granger proxy', f8)

# ============================================================
# Factor 9: Price Gap OI Elasticity
# 跳空幅度对OI变化的弹性
# ============================================================
print("=== Factor 9: gap_oi_elasticity ===")
gap = df['open'] / df['close'].shift(1) - 1
oi_chg_pct = df['open_interest'].pct_change()
elasticity = oi_chg_pct / gap.replace(0, np.nan)
elasticity = elasticity.clip(-10, 10)
el_z = (elasticity - elasticity.rolling(60).mean()) / elasticity.rolling(60).std().replace(0, np.nan)
f9 = el_z.rolling(10).mean()
test_factor('gap_oi_elasticity',
    '跳空OI弹性：OI变化率对跳空幅度的弹性系数z-score均值',
    'gap to OI elasticity', f9)

# ============================================================
# Factor 10: Weighted OI Price Comovement
# 加权OI价格协动：高OI变化时价格方向的加权累积
# ============================================================
print("=== Factor 10: weighted_oi_price_comove ===")
oi_chg_abs = df['open_interest'].diff().abs()
oi_weight = oi_chg_abs / oi_chg_abs.rolling(20).mean().replace(0, np.nan)
oi_weight = oi_weight.clip(0, 5)
price_dir = np.sign(df['close'].pct_change())
oi_dir = np.sign(df['open_interest'].diff())
comove = oi_weight * price_dir * oi_dir
comove_cum = comove.rolling(15).sum()
comove_z = (comove_cum - comove_cum.rolling(60).mean()) / comove_cum.rolling(60).std().replace(0, np.nan)
f10 = comove_z
test_factor('weighted_oi_price_comove',
    '加权OI价格协动：OI变化幅度加权的价格OI同向性累积z-score',
    'weighted OI price comovement', f10)

print("\n=== BATCH COMPLETE ===")
