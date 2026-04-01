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
# Factor 1: OI MACD Histogram
# OI的MACD柱状图：快慢OI EMA差的信号线偏离
# ============================================================
print("=== Factor 1: oi_macd_hist ===")
oi = df['open_interest']
oi_fast = oi.ewm(span=12).mean()
oi_slow = oi.ewm(span=26).mean()
oi_macd = oi_fast - oi_slow
oi_signal = oi_macd.ewm(span=9).mean()
oi_hist = oi_macd - oi_signal
oi_hist_z = (oi_hist - oi_hist.rolling(60).mean()) / oi_hist.rolling(60).std().replace(0, np.nan)
test_factor('oi_macd_hist',
    'OI MACD柱状图：OI快慢EMA差减信号线的z-score',
    'MACD histogram applied to OI', oi_hist_z)

# ============================================================
# Factor 2: OI Bollinger Band Width
# OI布林带宽度：OI波动率的度量
# ============================================================
print("=== Factor 2: oi_bb_width ===")
oi_ma = df['open_interest'].rolling(20).mean()
oi_std = df['open_interest'].rolling(20).std()
oi_bbw = oi_std / oi_ma.replace(0, np.nan)
oi_bbw_z = (oi_bbw - oi_bbw.rolling(60).mean()) / oi_bbw.rolling(60).std().replace(0, np.nan)
# 低波动后突破
price_dir = np.sign(df['close'].pct_change(10))
f2 = -oi_bbw_z * price_dir  # 低OI波动+有动量=好信号
test_factor('oi_bb_width',
    'OI布林带宽度取反：OI波动率z取反乘以价格动量方向',
    'OI Bollinger Band width inverted', f2)

# ============================================================
# Factor 3: OI RSI
# OI的RSI指标
# ============================================================
print("=== Factor 3: oi_rsi ===")
oi_chg = df['open_interest'].diff()
gain = oi_chg.clip(lower=0).rolling(14).mean()
loss = (-oi_chg).clip(lower=0).rolling(14).mean()
rs = gain / loss.replace(0, np.nan)
oi_rsi = 100 - 100 / (1 + rs)
oi_rsi_centered = oi_rsi - 50
oi_rsi_z = (oi_rsi_centered - oi_rsi_centered.rolling(60).mean()) / oi_rsi_centered.rolling(60).std().replace(0, np.nan)
test_factor('oi_rsi',
    'OI RSI指标：OI的14期RSI居中后的z-score',
    'RSI applied to OI', oi_rsi_z)

# ============================================================
# Factor 4: OI Stochastic
# OI随机指标：OI在近期区间中的位置
# ============================================================
print("=== Factor 4: oi_stochastic ===")
oi_high = df['open_interest'].rolling(20).max()
oi_low = df['open_interest'].rolling(20).min()
oi_k = (df['open_interest'] - oi_low) / (oi_high - oi_low).replace(0, np.nan)
oi_k_centered = oi_k - 0.5
oi_k_z = (oi_k_centered - oi_k_centered.rolling(60).mean()) / oi_k_centered.rolling(60).std().replace(0, np.nan)
test_factor('oi_stochastic',
    'OI随机指标：OI在20期高低区间中位置居中后的z-score',
    'Stochastic oscillator applied to OI', oi_k_z)

# ============================================================
# Factor 5: OI Volume Ratio Trend
# OI/成交量比率趋势：持仓集中度的趋势
# ============================================================
print("=== Factor 5: oi_vol_ratio_trend ===")
oi_vol_ratio = df['open_interest'] / df['volume'].replace(0, np.nan)
ratio_ma5 = oi_vol_ratio.rolling(5).mean()
ratio_ma20 = oi_vol_ratio.rolling(20).mean()
ratio_trend = ratio_ma5 - ratio_ma20
ratio_trend_z = (ratio_trend - ratio_trend.rolling(60).mean()) / ratio_trend.rolling(60).std().replace(0, np.nan)
test_factor('oi_vol_ratio_trend',
    'OI/成交量比率趋势：OI/Volume比率短长均线差z-score',
    'OI to volume ratio trend', ratio_trend_z)

# ============================================================
# Factor 6: Signed OI Acceleration
# 带符号OI加速度：OI加速度乘以价格动量
# ============================================================
print("=== Factor 6: signed_oi_accel ===")
oi_vel = df['open_interest'].diff(5)
oi_accel = oi_vel.diff(5)
oi_accel_z = (oi_accel - oi_accel.rolling(60).mean()) / oi_accel.rolling(60).std().replace(0, np.nan)
price_mom = np.sign(df['close'].pct_change(10))
f6 = oi_accel_z * price_mom
test_factor('signed_oi_accel',
    '带符号OI加速度：OI二阶导z-score乘以价格动量方向',
    'signed OI acceleration with price momentum', f6)

# ============================================================
# Factor 7: OI Trend Duration Score
# OI趋势持续期得分：OI连续同向变化的持续时间加权
# ============================================================
print("=== Factor 7: oi_trend_duration ===")
oi_dir = np.sign(df['open_interest'].diff())
# 计算连续同向持续期
duration = pd.Series(0.0, index=df.index)
for i in range(1, len(df)):
    if oi_dir.iloc[i] == oi_dir.iloc[i-1] and not np.isnan(oi_dir.iloc[i]):
        duration.iloc[i] = duration.iloc[i-1] + 1
    else:
        duration.iloc[i] = 1
signed_dur = duration * oi_dir
dur_z = (signed_dur - signed_dur.rolling(60).mean()) / signed_dur.rolling(60).std().replace(0, np.nan)
test_factor('oi_trend_duration',
    'OI趋势持续期：OI连续同向变化持续期数乘以方向的z-score',
    'OI trend duration score', dur_z)

# ============================================================
# Factor 8: OI Momentum Z-Score Composite
# OI动量z综合：多窗口OI动量z的加权平均
# ============================================================
print("=== Factor 8: oi_mom_z_composite ===")
composite = pd.Series(0.0, index=df.index)
weights = {5: 0.4, 10: 0.3, 20: 0.2, 40: 0.1}
for w, wt in weights.items():
    mom = df['open_interest'].pct_change(w)
    mom_z = (mom - mom.rolling(60).mean()) / mom.rolling(60).std().replace(0, np.nan)
    composite += wt * mom_z.fillna(0)
comp_z = (composite - composite.rolling(60).mean()) / composite.rolling(60).std().replace(0, np.nan)
test_factor('oi_mom_z_composite',
    'OI动量z综合：多窗口OI动量z-score的加权平均再标准化',
    'multi-window OI momentum z-score composite', comp_z)

# ============================================================
# Factor 9: Price OI Cointegration Speed
# 价格OI协整调整速度：偏离均衡后的回归速度
# ============================================================
print("=== Factor 9: price_oi_coint_speed ===")
p_z = (df['close'] - df['close'].rolling(60).mean()) / df['close'].rolling(60).std().replace(0, np.nan)
oi_z = (df['open_interest'] - df['open_interest'].rolling(60).mean()) / df['open_interest'].rolling(60).std().replace(0, np.nan)
spread = p_z - oi_z
spread_vel = spread.diff(5)
# 负速度=回归中，正速度=背离中
speed_z = (spread_vel - spread_vel.rolling(60).mean()) / spread_vel.rolling(60).std().replace(0, np.nan)
test_factor('price_oi_coint_speed',
    '价格OI协整速度：价格z与OI z之差的变化速度z-score',
    'price OI cointegration adjustment speed', speed_z)

# ============================================================
# Factor 10: OI Weighted Price Momentum
# OI加权价格动量：OI水平加权的价格动量
# ============================================================
print("=== Factor 10: oi_weighted_price_mom ===")
p_mom = df['close'].pct_change(10)
oi_level = df['open_interest'].rolling(100).rank(pct=True)
weighted_mom = p_mom * oi_level
wm_z = (weighted_mom - weighted_mom.rolling(60).mean()) / weighted_mom.rolling(60).std().replace(0, np.nan)
test_factor('oi_weighted_price_mom',
    'OI加权价格动量：OI水平分位数加权的价格动量z-score',
    'OI level weighted price momentum', wm_z)

print("\n=== BATCH 5 COMPLETE ===")
