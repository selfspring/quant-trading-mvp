import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()

    # 查看所有 varchar 字段
    print("=== 当前 varchar 字段 ===")
    cur.execute("""
        SELECT table_name, column_name, character_maximum_length 
        FROM information_schema.columns 
        WHERE character_maximum_length IS NOT NULL 
        AND table_schema = 'public' 
        ORDER BY table_name, column_name
    """)
    for row in cur.fetchall():
        print(row)

    # 找到 trace_id 相关字段并修复
    print("\n=== 修复 trace_id 字段 ===")
    cur.execute("""
        SELECT table_name, column_name, character_maximum_length 
        FROM information_schema.columns 
        WHERE column_name = 'trace_id' AND table_schema = 'public'
    """)
    fields = cur.fetchall()
    for table, col, length in fields:
        print(f"发现: {table}.{col} varchar({length})")
        if length < 64:
            cur.execute(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE varchar(64)")
            print(f"已扩展: {table}.{col} -> varchar(64)")

    conn.commit()
    print("\n完成！")
