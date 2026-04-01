import sys
sys.path.insert(0, r'E:\quant-trading-mvp')

import pandas as pd
from quant.signal_generator.ml_predictor import MLPredictor
from quant.common.config import config
from quant.common.db import db_engine

with db_engine(config) as engine:
    df = pd.read_sql(
        "SELECT time as timestamp, open, high, low, close, volume, "
        "COALESCE(open_interest, 0) as open_interest "
        "FROM kline_data WHERE symbol = 'au_main' AND interval = '30m' "
        "ORDER BY time DESC LIMIT 100",
        engine
    )

print('ROWS:', len(df))

if len(df) >= 60:
    df = df.sort_values('timestamp').reset_index(drop=True)
    predictor = MLPredictor()
    result = predictor.predict(df)
    print('Signal:', result)
    print('Current_price:', float(df.iloc[-1]['close']))
else:
    print('NOT_ENOUGH_DATA')
