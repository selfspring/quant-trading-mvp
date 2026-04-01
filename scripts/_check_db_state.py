#!/usr/bin/env python3
"""Temporary script to check DB schema state for verification validation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from quant.common.config import config

conn = psycopg2.connect(
    host=config.database.host,
    port=config.database.port,
    dbname=config.database.database,
    user=config.database.user,
    password=config.database.password.get_secret_value(),
)
cur = conn.cursor()

# Check news_analysis columns
cur.execute("""SELECT column_name, data_type FROM information_schema.columns
               WHERE table_name = 'news_analysis' ORDER BY ordinal_position""")
print('=== news_analysis columns ===')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Check if news_verification table exists
cur.execute("""SELECT EXISTS (
    SELECT 1 FROM information_schema.tables WHERE table_name = 'news_verification'
)""")
print(f'\nnews_verification table exists: {cur.fetchone()[0]}')

# Check record count in news_analysis
cur.execute('SELECT COUNT(*) FROM news_analysis')
print(f'news_analysis record count: {cur.fetchone()[0]}')

# Check time field population
cur.execute('SELECT COUNT(*) FROM news_analysis WHERE effective_time IS NOT NULL')
print(f'records with effective_time: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM news_analysis WHERE published_time IS NOT NULL')
print(f'records with published_time: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM news_analysis WHERE analyzed_at IS NOT NULL')
print(f'records with analyzed_at: {cur.fetchone()[0]}')

# Check a sample record
cur.execute("""SELECT id, news_id, time, published_time, analyzed_at, effective_time, direction, importance
               FROM news_analysis LIMIT 3""")
rows = cur.fetchall()
print('\n=== sample news_analysis records ===')
for r in rows:
    print(f'  id={r[0]}, news_id={r[1]}, time={r[2]}, pub={r[3]}, analyzed={r[4]}, eff={r[5]}, dir={r[6]}, imp={r[7]}')

# Check news_raw
cur.execute('SELECT COUNT(*) FROM news_raw')
print(f'\nnews_raw record count: {cur.fetchone()[0]}')

cur.close()
conn.close()
print('\n[check complete]')
