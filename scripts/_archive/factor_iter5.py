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

# Factor 1: OI加权的价格动量衰减
def oi_price_mom_decay(df):
    ret = df['close'].pct_change()
    oi_dir = np.sign(df['open_interest'].diff())
    # OI方向一致的收益累积，指数衰减
    aligned = ret * oi_dir
    signal = aligned.ewm(span=20).mean()
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 1: oi_price_mom_decay ===')
if evaluate_and_log('oi_price_mom_decay',
    'OI价格动量衰减：OI方向一致收益的EWM累积z-score',
    'OI aligned price momentum exponential decay',
    oi_price_mom_decay(df)):
    effective_count += 1

# Factor 2: 成交量冲击后OI反应延迟
def vol_shock_oi_lag(df, vol_threshold=2.0, lag=3):
    rel_vol = df['volume'] / df['volume'].rolling(40).mean()
    shock = (rel_vol > vol_threshold).astype(float)
    # 放量冲击后lag期的OI方向
    oi_after = df['open_interest'].diff(lag).shift(-lag)
    # 用当前可用信息：过去的冲击后OI反应模式
    oi_reaction = (shock.shift(lag) * df['open_interest'].diff()).rolling(20).mean()
    z = (oi_reaction - oi_reaction.rolling(60).mean()) / (oi_reaction.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 2: vol_shock_oi_lag ===')
if evaluate_and_log('vol_shock_oi_lag',
    '放量冲击OI滞后反应：放量后OI变化方向累积z-score',
    'volume shock OI lagged reaction',
    vol_shock_oi_lag(df)):
    effective_count += 1

# Factor 3: OI与价格的条件相关 - 上涨vs下跌时
def oi_price_cond_corr(df, window=30):
    ret = df['close'].pct_change()
    oi_chg = df['open_interest'].pct_change()
    # 上涨时的相关性
    up_ret = ret.where(ret > 0, 0)
    up_oi = oi_chg.where(ret > 0, 0)
    corr_up = up_ret.rolling(window).corr(up_oi)
    # 下跌时的相关性
    dn_ret = ret.where(ret <= 0, 0)
    dn_oi = oi_chg.where(ret <= 0, 0)
    corr_dn = dn_ret.rolling(window).corr(dn_oi)
    signal = (corr_up.fillna(0) - corr_dn.fillna(0))
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 3: oi_price_cond_corr ===')
if evaluate_and_log('oi_price_cond_corr',
    'OI价格条件相关：上涨vs下跌时OI相关性差z-score',
    'OI price conditional correlation up vs down',
    oi_price_cond_corr(df)):
    effective_count += 1

# Factor 4: OI加权的K线实体比
def oi_body_ratio(df, window=10):
    body = (df['close'] - df['open']).abs()
    total = df['high'] - df['low'] + 1e-10
    body_ratio = body / total
    oi_chg = df['open_interest'].diff()
    oi_dir = np.sign(oi_chg.rolling(5).mean())
    price_dir = np.sign(df['close'] - df['open'])
    # 大实体+OI方向一致=强势
    signal = body_ratio * price_dir * oi_dir
    signal_ma = signal.rolling(window).mean()
    z = (signal_ma - signal_ma.rolling(60).mean()) / (signal_ma.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 4: oi_body_ratio ===')
if evaluate_and_log('oi_body_ratio',
    'OI K线实体比：实体比乘以价格方向乘以OI方向z-score',
    'OI weighted candlestick body ratio',
    oi_body_ratio(df)):
    effective_count += 1

# Factor 5: OI变化的运行长度
def oi_run_length(df):
    oi_dir = np.sign(df['open_interest'].diff())
    # 连续同方向的运行长度
    run = pd.Series(0, index=df.index, dtype=float)
    for i in range(1, len(df)):
        if oi_dir.iloc[i] == oi_dir.iloc[i-1] and oi_dir.iloc[i] != 0:
            run.iloc[i] = run.iloc[i-1] + oi_dir.iloc[i]
        else:
            run.iloc[i] = oi_dir.iloc[i]
    z = (run - run.rolling(60).mean()) / (run.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 5: oi_run_length ===')
if evaluate_and_log('oi_run_length',
    'OI运行长度：OI连续同方向变化的累积长度z-score',
    'OI consecutive direction run length',
    oi_run_length(df)):
    effective_count += 1

# Factor 6: 价格波动率regime下的OI信号
def vol_regime_oi_signal(df, vol_window=20, pct_window=120):
    ret = df['close'].pct_change()
    vol = ret.rolling(vol_window).std()
    vol_pct = vol.rolling(pct_window).rank(pct=True)
    oi_mom = df['open_interest'].diff(10).rolling(5).mean()
    oi_z = (oi_mom - oi_mom.rolling(60).mean()) / (oi_mom.rolling(60).std() + 1e-10)
    # 低波动率regime下OI信号权重更高（蓄势）
    # 高波动率regime下OI信号权重降低（噪音大）
    weight = 2 - vol_pct  # 低波动=高权重
    signal = oi_z * weight
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 6: vol_regime_oi_signal ===')
if evaluate_and_log('vol_regime_oi_signal',
    '波动率Regime OI信号：低波动时OI信号增强z-score',
    'volatility regime weighted OI signal',
    vol_regime_oi_signal(df)):
    effective_count += 1

# Factor 7: OI与成交量的比率趋势
def oi_vol_ratio_trend(df, window=20):
    ratio = df['open_interest'] / (df['volume'].rolling(5).mean() + 1e-10)
    ratio_mom = ratio.diff(window)
    oi_dir = np.sign(df['open_interest'].diff(10).rolling(5).mean())
    signal = ratio_mom * oi_dir
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 7: oi_vol_ratio_trend ===')
if evaluate_and_log('oi_vol_ratio_trend',
    'OI成交量比率趋势：OI/Volume比率动量乘以OI方向z',
    'OI volume ratio trend with direction',
    oi_vol_ratio_trend(df)):
    effective_count += 1

# Factor 8: 价格与OI的Spearman秩相关变化率
def price_oi_spearman_roc(df, window=20):
    ret = df['close'].pct_change()
    oi_ret = df['open_interest'].pct_change()
    spearman = ret.rolling(window).corr(oi_ret)
    roc = spearman.diff(5)
    oi_dir = np.sign(df['open_interest'].diff(10).rolling(5).mean())
    signal = roc * oi_dir
    z = (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)
    return z.clip(-3, 3)

print('=== Factor 8: price_oi_spearman_roc ===')
if evaluate_and_log('price_oi_spearman_roc',
    '价���OI Spearman变化率：秩相关变化率乘以OI方向z',
    'price OI Spearman correlation rate of change',
    price_oi_spearman_roc(df)):
    effective_count += 1

print(f'\n=== BATCH 5 COMPLETE: 8 factors tested, {effective_count} effective ===')
