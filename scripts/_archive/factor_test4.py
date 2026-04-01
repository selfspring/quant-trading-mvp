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

def to_native(obj):
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, (np.bool_,)): return bool(obj)
    return obj

def test_and_log(name, description, source, factor_func):
    factor_values = factor_func(df)
    print(f"\n=== {name} ===")
    print(f"NaN ratio: {factor_values.isna().mean():.2%}")
    results = {}
    for h in [4, 8, 16]:
        fwd = np.log(df['close'].shift(-h) / df['close'])
        r = evaluate_factor(factor_values, fwd, name=name)
        results[f"{h*30//60}h"] = r
        print(f"  {h*30//60}h: IC={r.get('rank_ic',0):.4f}, IR={r.get('ir',0):.4f}, Dir={r.get('direction_acc',0):.4f}")
    avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results if results[k].get('valid')])
    effective = avg_ic > 0.02
    record = {
        'timestamp': datetime.now().isoformat(),
        'name': name, 'description': description, 'source': source,
        'avg_abs_ic': round(float(avg_ic), 4),
        'results': {k: {kk: to_native(round(float(vv),4)) if isinstance(vv,(float,np.floating)) else to_native(vv)
                        for kk, vv in v.items() if kk != 'valid'} for k, v in results.items()},
        'effective': bool(effective),
    }
    with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    print(f"Avg |IC|: {avg_ic:.4f} {'** EFFECTIVE **' if effective else ''}")
    return avg_ic, effective

# ============================================================
# Factor 25: ATR Breakout (ATR突破因子)
# 价格变动相对于ATR的比例
# ============================================================
def atr_breakout(df):
    atr = (df['high'] - df['low']).rolling(14).mean()
    move = df['close'] - df['close'].shift(1)
    return (move / (atr + 1e-8)).rolling(5).sum()

test_and_log('atr_breakout', 'ATR突破：价格变动/ATR的5期累计',
             'ATR breakout system', atr_breakout)

# ============================================================
# Factor 26: Close-to-High Ratio (收盘接近最高价比率)
# 收盘越接近最高价，多头越强
# ============================================================
def close_to_high_ratio(df):
    ratio = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)
    return ratio.rolling(10).mean() * 2 - 1

test_and_log('close_to_high_ratio', '收盘接近最高价比率：(C-L)/(H-L)的10期均值',
             'price position analysis', close_to_high_ratio)

# ============================================================
# Factor 27: Volume Trend (成交量趋势)
# 成交量的线性回归斜率
# ============================================================
def volume_trend(df):
    def slope(x):
        n = len(x)
        if n < 2: return 0
        t = np.arange(n)
        return np.polyfit(t, x, 1)[0]
    vol_slope = df['volume'].rolling(20).apply(slope, raw=True)
    # 归一化
    return vol_slope / (df['volume'].rolling(20).mean() + 1e-8)

test_and_log('volume_trend', '成交量趋势：20期成交量线性回归斜率，归一化',
             'volume trend analysis', volume_trend)

# ============================================================
# Factor 28: OI Regime (持仓量状态)
# 持仓量处于高位还是低位
# ============================================================
def oi_regime(df):
    oi_pct = df['open_interest'].rolling(100).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    price_ret = df['close'].pct_change(10)
    # 高持仓+上涨=趋势确认，高持仓+下跌=趋势确认
    return oi_pct * price_ret * 100

test_and_log('oi_regime', '持仓量状态：100期持仓量分位数*10期收益率',
             'OI regime factor', oi_regime)

# ============================================================
# Factor 29: Overnight Gap Persistence (隔夜跳空持续性)
# ============================================================
def overnight_gap_persistence(df):
    gap = df['open'] - df['close'].shift(1)
    gap_dir = np.sign(gap)
    # 跳空方向的持续性
    persistence = gap_dir.rolling(10).sum() / 10
    return persistence

test_and_log('overnight_gap_persistence', '隔夜跳空持续性：10期跳空方向的一致性',
             'gap persistence', overnight_gap_persistence)

# ============================================================
# Factor 30: Price Efficiency (价格效率)
# 净位移/总路径长度
# ============================================================
def price_efficiency(df):
    net_move = abs(df['close'] - df['close'].shift(10))
    total_path = abs(df['close'].diff()).rolling(10).sum()
    efficiency = net_move / (total_path + 1e-8)
    # 高效率=趋势，低效率=震荡
    price_dir = np.sign(df['close'] - df['close'].shift(10))
    return efficiency * price_dir

test_and_log('price_efficiency', '价格效率：10期净位移/总路径，带方向',
             'fractal efficiency ratio', price_efficiency)

# ============================================================
# Factor 31: OI Concentration Momentum (持仓集中度动量)
# ============================================================
def oi_concentration_momentum(df):
    oi_ratio = df['open_interest'] / (df['volume'] + 1e-8)
    oi_ratio_ma = oi_ratio.rolling(20).mean()
    # 持仓集中度的变化趋势
    return (oi_ratio - oi_ratio_ma) / (oi_ratio.rolling(20).std() + 1e-8)

test_and_log('oi_concentration_momentum', '持仓集中度动量：OI/Volume比值偏离20期均值的z-score',
             'OI concentration dynamics', oi_concentration_momentum)

# ============================================================
# Factor 32: Volatility Asymmetry (波动率不对称性)
# 上行波动 vs 下行波动
# ============================================================
def volatility_asymmetry(df):
    ret = np.log(df['close'] / df['close'].shift(1))
    up_vol = ret.where(ret > 0, 0).rolling(20).std()
    down_vol = ret.where(ret < 0, 0).rolling(20).std()
    return (up_vol - down_vol) / (up_vol + down_vol + 1e-8)

test_and_log('volatility_asymmetry', '波动率不对称性：上行波动率与下行波动率之差/之和',
             'volatility asymmetry', volatility_asymmetry)

print("\n" + "="*60)
print("ROUND 4 COMPLETE")
print("="*60)
