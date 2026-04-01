"""
宏观经济事件历史数据采集（FRED API 真实数据）

数据源：St. Louis Fed FRED API
- NFP  (release_id=50):  Employment Situation
- CPI  (release_id=10):  Consumer Price Index
- PPI  (release_id=46):  Producer Price Index
- GDP  (release_id=53):  Gross Domestic Product
- PCE  (release_id=54):  Personal Income and Outlays
- FOMC_MINUTES: 从美联储官网真实发布日期（federalreserve.gov）

覆盖范围：2013-01-01 ~ 2026-03-21
"""
import sys
import io
import json
import time
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import psycopg2

FRED_API_KEY = '4a2f776eaba16b7aa835947dbc060a99'
FRED_BASE = 'https://api.stlouisfed.org/fred'

# 各指标 FRED release_id 和发布时间（美东 ET）
RELEASES = [
    {'event_type': 'NFP',  'release_id': 50,  'release_time_utc': '13:30:00', 'description': 'Non-Farm Payrolls (Employment Situation)'},
    {'event_type': 'CPI',  'release_id': 10,  'release_time_utc': '13:30:00', 'description': 'Consumer Price Index'},
    {'event_type': 'PPI',  'release_id': 46,  'release_time_utc': '13:30:00', 'description': 'Producer Price Index'},
    {'event_type': 'GDP',  'release_id': 53,  'release_time_utc': '13:30:00', 'description': 'Gross Domestic Product'},
    {'event_type': 'PCE',  'release_id': 54,  'release_time_utc': '13:30:00', 'description': 'Personal Income and Outlays (PCE)'},
]


def fetch_fred_release_dates(release_id: int, start: str = '2013-01-01', end: str = '2026-03-21') -> list:
    """从 FRED API 获取某个 release 的历史发布日期"""
    url = (
        f"{FRED_BASE}/release/dates"
        f"?release_id={release_id}"
        f"&realtime_start={start}"
        f"&realtime_end={end}"
        f"&api_key={FRED_API_KEY}"
        f"&file_type=json"
        f"&limit=1000"
    )
    resp = requests.get(url, timeout=30, proxies={'http': None, 'https': None})
    resp.raise_for_status()
    data = resp.json()
    return [d['date'] for d in data.get('release_dates', [])]


def generate_fomc_minutes(start_year: int = 2013, end_year: int = 2026) -> list:
    """FOMC 会议纪要：使用美联储官网真实发布日期（非推算）
    
    数据来源:
    - 2021-2026: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
    - 2013-2020: https://www.federalreserve.gov/monetarypolicy/fomchistorical{YEAR}.htm
    """
    import importlib, sys
    # 动态导入同目录下的 fetch_fomc_minutes_real 模块
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    mod = importlib.import_module('fetch_fomc_minutes_real')
    
    events = mod.build_events()
    # 按年份过滤
    events = [e for e in events if start_year <= e['year'] <= end_year]
    return events


def save_to_db(events: list) -> int:
    conn = psycopg2.connect(
        host='localhost', port=5432, database='quant_trading',
        user='postgres', password='@Cmx1454697261'
    )
    cur = conn.cursor()
    inserted = 0
    for e in events:
        try:
            cur.execute("""
                INSERT INTO macro_events
                    (event_type, event_date, event_time_utc, year, month,
                     importance, description, source, source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_type, event_date) DO NOTHING
            """, (
                e['event_type'], e['event_date'], e['event_time_utc'],
                e['year'], e['month'], e['importance'],
                e.get('description', ''), e.get('source', ''),
                e.get('source_url', ''),
            ))
            if cur.rowcount > 0:
                inserted += 1
        except Exception as ex:
            print(f"  Skip {e['event_type']} {e['event_date']}: {ex}")
    conn.commit()
    conn.close()
    return inserted


def main():
    all_events = []
    stats = {}

    # 1. 从 FRED API 获取各指标历史发布日期
    for rel in RELEASES:
        etype = rel['event_type']
        print(f"获取 {etype} (release_id={rel['release_id']})...")
        try:
            dates = fetch_fred_release_dates(rel['release_id'])
            events = []
            for d_str in dates:
                d = date.fromisoformat(d_str)
                events.append({
                    'event_type': etype,
                    'event_date': d_str,
                    'event_time_utc': f"{d_str}T{rel['release_time_utc']}Z",
                    'year': d.year,
                    'month': d.month,
                    'importance': 'high',
                    'description': rel['description'],
                    'source': 'fred.stlouisfed.org',
                    'source_url': f"https://fred.stlouisfed.org/releases/dates/{rel['release_id']}",
                })
            stats[etype] = len(events)
            all_events.extend(events)
            print(f"  {len(events)} 条 ({dates[0] if dates else 'N/A'} ~ {dates[-1] if dates else 'N/A'})")
            time.sleep(0.5)  # 礼貌限速
        except Exception as e:
            print(f"  失败: {e}")

    # 2. FOMC 会议纪要（从美联储官网真实发布日期）
    print("生成 FOMC_MINUTES...")
    minutes_events = generate_fomc_minutes()
    stats['FOMC_MINUTES'] = len(minutes_events)
    all_events.extend(minutes_events)
    print(f"  {len(minutes_events)} 条")

    # 3. 保存 JSON
    output_dir = Path(__file__).parent.parent / 'data'
    output_dir.mkdir(exist_ok=True)
    json_path = output_dir / 'macro_events_fred.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_events, f, indent=2, ensure_ascii=False)
    print(f"\n已保存 {len(all_events)} 条到 {json_path}")

    # 4. 入库
    print("\n=== 入库到 macro_events 表 ===")
    inserted = save_to_db(all_events)
    print(f"  新增 {inserted} 条")

    # 5. 数据库汇总
    conn = psycopg2.connect(
        host='localhost', port=5432, database='quant_trading',
        user='postgres', password='@Cmx1454697261'
    )
    cur = conn.cursor()
    cur.execute("SELECT event_type, COUNT(*), MIN(event_date), MAX(event_date) FROM macro_events GROUP BY event_type ORDER BY event_type")
    print("\n=== 数据库 macro_events 完整统计 ===")
    total = 0
    for row in cur.fetchall():
        print(f"  {row[0]:15s}: {row[1]:4d} 条  ({row[2]} ~ {row[3]})")
        total += row[1]
    print(f"  {'总计':15s}: {total} 条")
    conn.close()


if __name__ == '__main__':
    main()
