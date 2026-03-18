from quant.common.db import db_engine
from quant.common.config import config
import pandas as pd

with db_engine(config) as engine:
    df = pd.read_sql("SELECT table_name FROM information_schema.tables WHERE table_schema='public'", engine)
    print(df.to_string())
