#!/usr/bin/env python3
"""
宏观数据导入脚本
将 data/external/macro/ 下的 CSV 文件导入 PostgreSQL macro_data 表
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
from datetime import datetime

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'quant_trading',
    'user': 'postgres',
    'password': '@Cmx1454697261'
}

# 数据文件映射
DATA_FILES = {
    'cpi_cn_daily.csv': {
        'indicator': 'CPI_CN',
        'value_col': 'cpi',
        'unit': 'index',
        'source': 'NBS'
    },
    'cpi_usa_daily.csv': {
        'indicator': 'CPI_USA',
        'value_col': 'cpi',
        'unit': 'index',
        'source': 'BLS'
    },
    'fed_funds_rate.csv': {
        'indicator': 'FED_FUNDS_RATE',
        'value_col': 'rate',
        'unit': 'percent',
        'source': 'Federal Reserve'
    },
    'us10y_daily.csv': {
        'indicator': 'US10Y_YIELD',
        'value_col': 'yield',
        'unit': 'percent',
        'source': 'US Treasury'
    }
}

def connect_db():
    """连接数据库"""
    return psycopg2.connect(**DB_CONFIG)

def import_file(conn, file_path, config):
    """导入单个文件"""
    print(f"\n导入文件: {file_path.name}")
    
    # 读取 CSV
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'])
    
    # 准备插入数据
    records = []
    for _, row in df.iterrows():
        records.append((
            row['date'],
            config['indicator'],
            float(row[config['value_col']]),
            config['unit'],
            config['source']
        ))
    
    # 批量插入
    cursor = conn.cursor()
    insert_sql = """
        INSERT INTO macro_data (time, indicator, value, unit, source)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (time, indicator) DO UPDATE
        SET value = EXCLUDED.value,
            unit = EXCLUDED.unit,
            source = EXCLUDED.source
    """
    
    execute_batch(cursor, insert_sql, records, page_size=100)
    conn.commit()
    
    print(f"[OK] 导入 {len(records)} 条记录 - {config['indicator']}")
    return len(records)

def main():
    """主函数"""
    print("=" * 60)
    print("宏观数据导入工具")
    print("=" * 60)
    
    data_dir = Path('data/external/macro')
    
    if not data_dir.exists():
        print(f"错误: 数据目录不存在 - {data_dir}")
        return
    
    # 连接数据库
    try:
        conn = connect_db()
        print("[OK] 数据库连接成功")
    except Exception as e:
        print(f"[ERROR] 数据库连接失败: {e}")
        return
    
    # 导入每个文件
    total_records = 0
    results = {}
    
    for filename, config in DATA_FILES.items():
        file_path = data_dir / filename
        
        if not file_path.exists():
            print(f"[WARN] 文件不存在: {filename}")
            continue
        
        try:
            count = import_file(conn, file_path, config)
            results[config['indicator']] = count
            total_records += count
        except Exception as e:
            print(f"[ERROR] 导入失败 {filename}: {e}")
            conn.rollback()
    
    conn.close()
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("导入完成")
    print("=" * 60)
    for indicator, count in results.items():
        print(f"  {indicator:20s}: {count:4d} 条")
    print(f"\n  总计: {total_records} 条记录")
    print("=" * 60)

if __name__ == '__main__':
    main()
