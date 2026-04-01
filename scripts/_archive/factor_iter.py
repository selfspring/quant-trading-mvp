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

def evaluate_and_log(name, description, source, factor_values):
    results = {}
    for h in [4, 8, 16]:
        fwd = np.log(df['close'].shift(-h) / df['close'])
        r = evaluate_factor(factor_values, fwd, name=name)
        results[f'{h*30//60}h'] = r
        print(f'  {name} {h*30//60}h: IC={r.get("rank_ic",0):.4f}, IR={r.get("ir",0):.4f}, Dir={r.get("direction_acc",0):.4f}')
    avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results if results[k].get('valid')])
    record = {
        'timestamp': datetime.now().isoformat(),
        'name': name,
        'description': description,
        'source': source,
        'avg_abs_ic': round(float(avg_ic), 4),
        'results': {k: {kk: (float(vv) if isinstance(vv, (np.floating, np.integer)) else vv) for kk, vv in v.items() if kk != 'valid'} for k, v in results.items()},
        'effective': bool(avg_ic > 0.02),
    }
    with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    tag = '** EFFECTIVE **' if avg_ic > 0.02 else ''
    print(f'  => Avg |IC|: {avg_ic:.4f} {tag}\n')
    return avg_ic > 0.02

effective_count = 0

# Factor 1: OI Hurst指数代理
def oi_hurst_proxy(df, window=40):
    oi = df['open_interest']
    oi_diff = oi.diff().fillna(0)
    def hurst_rs(series):
        if len(series) < 10 or series.std() == 0:
            return 0.5
        mean_adj = series - series.mean()
        cumdev = mean_adj.cumsum()
        R = cumdev.max() - cumdev.min()
        S = series.std()
        if S == 0: return 0.5
        return np.log(max(R/S, 1e-10)) / np.log(len(series))
    hurst = oi_diff.rolling(window).apply(hurst_rs, raw=True)
    oi_dir = np.sign(oi.diff(10).rolling(5).mean())
    signal = (hurst - 0.5) * oi_dir
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 1: oi_hurst_proxy ===')
if evaluate_and_log('oi_hurst_proxy',
    'OI Hurst指数代理：R/S分析���计OI趋势持续性乘以OI方向z-score',
    'Hurst exponent R/S analysis on OI',
    oi_hurst_proxy(df)):
    effective_count += 1

# Factor 2: OI与价格的滚动互信息代理
def oi_price_mi_proxy(df, window=30):
    ret = df['close'].pct_change()
    oi_ret = df['open_interest'].pct_change()
    # 用rank correlation的绝对值作为MI代理
    mi = ret.rolling(window).corr(oi_ret).abs()
    oi_dir = np.sign(df['open_interest'].diff(10).rolling(5).mean())
    signal = mi * oi_dir
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 2: oi_price_mi_proxy ===')
if evaluate_and_log('oi_price_mi_proxy',
    'OI价格互信息代理：滚动相关绝对值乘以OI方向z-score',
    'mutual information proxy via rolling correlation',
    oi_price_mi_proxy(df)):
    effective_count += 1

# Factor 3: OI变化率的条件异方差 - GARCH代理
def oi_garch_proxy(df, fast=10, slow=40):
    oi_ret = df['open_interest'].pct_change().fillna(0)
    # 用短期vs长期波动率比作为GARCH代理
    vol_fast = oi_ret.rolling(fast).std()
    vol_slow = oi_ret.rolling(slow).std()
    vol_ratio = vol_fast / (vol_slow + 1e-10)
    oi_dir = np.sign(df['open_interest'].diff(10).rolling(5).mean())
    # 高波动率比 = OI波动加速，跟随OI方向
    signal = vol_ratio * oi_dir
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 3: oi_garch_proxy ===')
if evaluate_and_log('oi_garch_proxy',
    'OI GARCH代理：OI变化率短长期波动率比乘以OI方向z-score',
    'GARCH proxy via OI volatility ratio',
    oi_garch_proxy(df)):
    effective_count += 1

# Factor 4: 价格OI联合极端事件
def price_oi_joint_extreme(df, window=40, threshold=1.5):
    ret_z = (df['close'].pct_change() - df['close'].pct_change().rolling(window).mean()) / (df['close'].pct_change().rolling(window).std() + 1e-10)
    oi_z = (df['open_interest'].pct_change() - df['open_interest'].pct_change().rolling(window).mean()) / (df['open_interest'].pct_change().rolling(window).std() + 1e-10)
    # 联合极端：价格和OI同时极端
    joint = ret_z * oi_z
    # 正值=同向极端（趋势确认），负值=反向极端（背离）
    signal = joint.ewm(span=10).mean()
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 4: price_oi_joint_extreme ===')
if evaluate_and_log('price_oi_joint_extreme',
    '价格OI联合极端：价格与OI标准化变化乘积的EMA z-score',
    'price OI joint extreme event interaction',
    price_oi_joint_extreme(df)):
    effective_count += 1

# Factor 5: OI变化的非对称性 - 上涨vs下跌时OI变化幅度差
def oi_asymmetry_factor(df, window=30):
    ret = df['close'].pct_change()
    oi_chg = df['open_interest'].diff()
    up_mask = (ret > 0).astype(float)
    down_mask = (ret <= 0).astype(float)
    oi_up = (oi_chg * up_mask).rolling(window).mean()
    oi_down = (oi_chg * down_mask).rolling(window).mean()
    asym = oi_up - oi_down  # 正=上涨时OI增加更多
    z = (asym - asym.rolling(60).mean()) / (asym.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 5: oi_asymmetry_factor ===')
if evaluate_and_log('oi_asymmetry_factor',
    'OI非对称性：上涨vs下跌时OI变化幅度差z-score',
    'OI change asymmetry up vs down bars',
    oi_asymmetry_factor(df)):
    effective_count += 1

# Factor 6: OI加权的价格动量质量 - Calmar比
def oi_weighted_calmar(df, window=40):
    ret = df['close'].pct_change()
    cum_ret = ret.rolling(window).sum()
    max_dd = ret.rolling(window).apply(lambda x: (np.maximum.accumulate(x.cumsum()) - x.cumsum()).max(), raw=True)
    calmar = cum_ret / (max_dd + 1e-10)
    oi_dir = np.sign(df['open_interest'].diff(10).rolling(5).mean())
    signal = calmar * oi_dir
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 6: oi_weighted_calmar ===')
if evaluate_and_log('oi_weighted_calmar',
    'OI加权Calmar比：价格动量Calmar比乘以OI方向z-score',
    'OI weighted Calmar ratio price momentum quality',
    oi_weighted_calmar(df)):
    effective_count += 1

# Factor 7: OI梯度场 - 多尺度OI梯度一致性
def oi_gradient_field(df):
    oi = df['open_interest']
    g5 = oi.diff(5) / 5
    g10 = oi.diff(10) / 10
    g20 = oi.diff(20) / 20
    g40 = oi.diff(40) / 40
    # 梯度一致性：所有梯度同号时信号强
    signs = np.sign(g5) + np.sign(g10) + np.sign(g20) + np.sign(g40)
    magnitude = (g5.abs() + g10.abs() + g20.abs() + g40.abs()) / 4
    signal = signs * magnitude
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 7: oi_gradient_field ===')
if evaluate_and_log('oi_gradient_field',
    'OI梯度场：多尺度OI梯度一致性乘以幅度z-score',
    'OI gradient field multi-scale consistency',
    oi_gradient_field(df)):
    effective_count += 1

# Factor 8: 价格波动率锥位置OI交互
def vol_cone_oi(df, window=20, long_window=120):
    ret = df['close'].pct_change()
    vol = ret.rolling(window).std()
    vol_pct = vol.rolling(long_window).rank(pct=True)
    oi_dir = np.sign(df['open_interest'].diff(10).rolling(5).mean())
    # 低波动率分位+OI方向 = 蓄势待发
    signal = (1 - vol_pct) * oi_dir
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 8: vol_cone_oi ===')
if evaluate_and_log('vol_cone_oi',
    '波动率锥位置OI：波动率历史分位取反乘以OI方向z-score',
    'volatility cone percentile with OI direction',
    vol_cone_oi(df)):
    effective_count += 1

print(f'\n=== BATCH COMPLETE: 8 factors tested, {effective_count} effective ===')
