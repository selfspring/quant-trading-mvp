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

# 因子 7: OI 波动率调整动量
def oi_vol_adj_momentum(df):
    oi_mom = df['open_interest'].pct_change(10)
    oi_vol = oi_mom.rolling(20).std()
    adj_mom = oi_mom / (oi_vol + 1e-8)
    signal = (adj_mom - adj_mom.rolling(60).mean()) / (adj_mom.rolling(60).std() + 1e-8)
    return signal

factor_values = oi_vol_adj_momentum(df)

results = {}
for h in [4, 8, 16]:
    fwd = np.log(df['close'].shift(-h) / df['close'])
    r = evaluate_factor(factor_values, fwd, name='oi_vol_adj_momentum')
    results[f'{h*30//60}h'] = r
    print(f"  {h*30//60}h: IC={r.get('rank_ic',0):.4f}, IR={r.get('ir',0):.4f}, Dir={r.get('direction_acc',0):.4f}")

avg_ic = np.mean([abs(results[k].get('rank_ic', 0)) for k in results if results[k].get('valid')])
effective = bool(avg_ic > 0.02)
record = {
    'timestamp': datetime.now().isoformat(),
    'name': 'oi_vol_adj_momentum',
    'description': 'OI 波动率调整动量：OI 动量除以其波动率',
    'source': 'OI volatility adjusted momentum',
    'avg_abs_ic': round(float(avg_ic), 4),
    'results': {k: {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv for kk, vv in v.items() if kk != 'valid'} for k, v in results.items()},
    'effective': effective,
    'code': 'def oi_vol_adj_momentum(df):\n    oi_mom = df["open_interest"].pct_change(10)\n    oi_vol = oi_mom.rolling(20).std()\n    adj_mom = oi_mom / (oi_vol + 1e-8)\n    signal = (adj_mom - adj_mom.rolling(60).mean()) / (adj_mom.rolling(60).std() + 1e-8)\n    return signal',
}
with open('E:/quant-trading-mvp/data/factor_discovery_log.jsonl', 'a', encoding='utf-8') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')
print(f"Avg |IC|: {avg_ic:.4f} {'** EFFECTIVE **' if effective else ''}")

if effective:
    with open('E:/quant-trading-mvp/quant/factors/discovered_factors.py', 'a', encoding='utf-8') as f:
        f.write('\n\n' + record['code'])
    print("Added to discovered_factors.py")
