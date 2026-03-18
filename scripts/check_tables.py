"""
检查数据库表结构
"""
import sys
sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()

    print("=" * 60)
    print("数据库表结构")
    print("=" * 60)

    # 列出所有表
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cur.fetchall()
    print(f'\n📋 所有表 ({len(tables)} 个):')
    for table in tables:
        print(f'  - {table[0]}')
        
        # 获取表的行数
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cur.fetchone()[0]
            print(f'    行数: {count:,}')
        except Exception as e:
            print(f'    无法查询: {e}')

    cur.close()

print("\n" + "=" * 60)
