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

# === 因子实现：Price OI Phase Difference ===
def price_oi_phase_diff(df):
    # 价格动量 (10 期)
    price_mom = df['close'].pct_change(10)
    # OI 动量 (10 期)
    oi_mom = df['open_interest'].pct_change(10)
    # 标准化
    price_z = (price_mom - price_mom.rolling(40, min_periods=20).mean()) / price_mom.rolling(40, min_periods=20).std()
    oi_z = (oi_mom - oi_mom.rolling(40, min_periods=20).mean()) / oi_mom.rolling(40, min_periods=20).std()
    # 相位差：两者差的绝对值表示不同步程度
    phase_diff = np.abs(price_z - oi_z)
    # 方向：当价格强于 OI 时看空（价格领先），反之为看多
    direction = np.sign(oi_z - price_z)
    # 信号：不同步程度 * 方向
    signal = phase_diff * direction
    # 平滑
    factor = signal.rolling(10, min_periods=5).mean()
    # 标准化
    factor = (factor - factor.rolling(60, min_periods=30).mean()) / factor.rolling(60, min_periods=30).std()
    return factor

factor_values = price_oi_phase_diff(df)

results = {}
for h in [4, 8, 16]:
    fwd = np.log(df['close'].shift(-h) / df['close'])
    r = evaluate_factor(factor_values, fwd, name='price_oi_phase_diff')
    results[f'{h*30//60}h'] = r
    print(f"  {h*30//60}h: IC={r.get('rank_ic',0):.4f}, IR={r.get('ir',0):.4f}, Dir={r.get('direction_acc',0):.4f}")

avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results if results[k].get('valid')])
effective = bool(avg_ic > 0.02)
record = {
    'timestamp': datetime.now().isoformat(),
    'name': 'price_oi_phase_diff',
    'description': '价格 OI 相位差：价格与 OI 动量不同步程度乘以方向',
    'source': 'phase difference between price and OI cycles',
    'avg_abs_ic': round(avg_ic, 4),
    'results': {k: {kk: vv for kk, vv in v.items() if kk != 'valid'} for k, v in results.items()},
    'effective': effective,
    'code': 'price_z - oi_z; phase_diff=|diff|; signal=phase_diff*sign(oi_z-price_z)',
}
with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')
status = '** EFFECTIVE **' if effective else ''
print(f"Avg |IC|: {avg_ic:.4f} {status}")
