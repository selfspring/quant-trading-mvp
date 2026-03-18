from quant.common.db import db_engine
from quant.common.config import config
import pandas as pd

with db_engine(config) as engine:
    df = pd.read_sql("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='kline_data' ORDER BY ordinal_position", engine)
    print(df.to_string())
    print()
    df2 = pd.read_sql("SELECT * FROM kline_data LIMIT 3", engine)
    print(df2.to_string())
