"""清除指定表的数据"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()

    tables = ['kline_daily', 'kline_data', 'macro_data', 'message_trace', 'news_raw']

    for name in tables:
        cur.execute(f'DELETE FROM "{name}"')
        print(f'{name}: deleted {cur.rowcount} rows')

    conn.commit()
print('Done.')
