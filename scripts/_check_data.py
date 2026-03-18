from quant.common.db import db_engine
from quant.common.config import config
import pandas as pd

with db_engine(config) as engine:
    df = pd.read_sql("SELECT DISTINCT symbol, interval, count(*) as cnt FROM kline_data GROUP BY symbol, interval ORDER BY symbol, interval", engine)
    print(df.to_string())
