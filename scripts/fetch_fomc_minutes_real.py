"""
替换 FOMC_MINUTES 推算日期为美联储官网真实发布日期

数据来源：
- 2021-2026: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- 2013-2020: https://www.federalreserve.gov/monetarypolicy/fomchistorical{YEAR}.htm

所有日期均从美联储官网直接提取，非推算值。
"""
import sys
import io
import json
import copy
import shutil
from datetime import date, datetime
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'quant_trading',
    'user': 'postgres',
    'password': '@Cmx1454697261',
}

# =====================================================================
# 所有数据均从美联储官网真实提取
# meeting_date -> release_date (FOMC Minutes 真实发布日期)
# =====================================================================

# 从 fomchistorical{YEAR}.htm 页面提取 (2013-2020)
HISTORICAL_DATA = {
    # 2013
    '2013-01-30': '2013-02-20',
    '2013-03-20': '2013-04-10',
    '2013-05-01': '2013-05-22',
    '2013-06-19': '2013-07-10',
    '2013-07-31': '2013-08-21',
    '2013-09-18': '2013-10-09',
    '2013-10-30': '2013-11-20',
    '2013-12-18': '2014-01-08',
    # 2014
    '2014-01-29': '2014-02-19',
    '2014-03-19': '2014-04-09',
    '2014-04-30': '2014-05-21',
    '2014-06-18': '2014-07-09',
    '2014-07-30': '2014-08-20',
    '2014-09-17': '2014-10-08',
    '2014-10-29': '2014-11-19',
    '2014-12-17': '2015-01-07',
    # 2015
    '2015-01-28': '2015-02-18',
    '2015-03-18': '2015-04-08',
    '2015-04-29': '2015-05-20',
    '2015-06-17': '2015-07-08',
    '2015-07-29': '2015-08-19',
    '2015-09-17': '2015-10-08',
    '2015-10-28': '2015-11-18',
    '2015-12-16': '2016-01-06',
    # 2016
    '2016-01-27': '2016-02-17',
    '2016-03-16': '2016-04-06',
    '2016-04-27': '2016-05-18',
    '2016-06-15': '2016-07-06',
    '2016-07-27': '2016-08-17',
    '2016-09-21': '2016-10-12',
    '2016-11-02': '2016-11-23',
    '2016-12-14': '2017-01-04',
    # 2017
    '2017-02-01': '2017-02-22',
    '2017-03-15': '2017-04-05',
    '2017-05-03': '2017-05-24',
    '2017-06-14': '2017-07-05',
    '2017-07-26': '2017-08-16',
    '2017-09-20': '2017-10-11',
    '2017-11-01': '2017-11-22',
    '2017-12-13': '2018-01-03',
    # 2018
    '2018-01-31': '2018-02-21',
    '2018-03-21': '2018-04-11',
    '2018-05-02': '2018-05-23',
    '2018-06-13': '2018-07-05',
    '2018-08-01': '2018-08-22',
    '2018-09-26': '2018-10-17',
    '2018-11-08': '2018-11-29',
    '2018-12-19': '2019-01-09',
    # 2019
    '2019-01-30': '2019-02-20',
    '2019-03-20': '2019-04-10',
    '2019-05-01': '2019-05-22',
    '2019-06-19': '2019-07-10',
    '2019-07-31': '2019-08-21',
    '2019-09-18': '2019-10-09',
    '2019-10-30': '2019-11-20',
    '2019-12-11': '2020-01-03',
    # 2020
    '2020-01-29': '2020-02-19',
    '2020-03-15': '2020-04-08',
    '2020-04-29': '2020-05-20',
    '2020-06-10': '2020-07-01',
    '2020-07-29': '2020-08-19',
    '2020-09-16': '2020-10-07',
    '2020-11-05': '2020-11-25',
    '2020-12-16': '2021-01-06',
}

# 从 fomccalendars.htm 页面提取 (2021-2026)
CALENDAR_DATA = {
    # 2021
    '2021-01-27': '2021-02-17',
    '2021-03-17': '2021-04-07',
    '2021-04-28': '2021-05-19',
    '2021-06-16': '2021-07-07',
    '2021-07-28': '2021-08-18',
    '2021-09-22': '2021-10-13',
    '2021-11-03': '2021-11-24',
    '2021-12-15': '2022-01-05',
    # 2022
    '2022-01-26': '2022-02-16',
    '2022-03-16': '2022-04-06',
    '2022-05-04': '2022-05-25',
    '2022-06-15': '2022-07-06',
    '2022-07-27': '2022-08-17',
    '2022-09-21': '2022-10-12',
    '2022-11-02': '2022-11-23',
    '2022-12-14': '2023-01-04',
    # 2023
    '2023-02-01': '2023-02-22',
    '2023-03-22': '2023-04-12',
    '2023-05-03': '2023-05-24',
    '2023-06-14': '2023-07-05',
    '2023-07-26': '2023-08-16',
    '2023-09-20': '2023-10-11',
    '2023-11-01': '2023-11-21',
    '2023-12-13': '2024-01-03',
    # 2024
    '2024-01-31': '2024-02-21',
    '2024-03-20': '2024-04-10',
    '2024-05-01': '2024-05-22',
    '2024-06-12': '2024-07-03',
    '2024-07-31': '2024-08-21',
    '2024-09-18': '2024-10-09',
    '2024-11-07': '2024-11-26',
    '2024-12-18': '2025-01-08',
    # 2025
    '2025-01-29': '2025-02-19',
    '2025-03-19': '2025-04-09',
    '2025-05-07': '2025-05-28',
    '2025-06-18': '2025-07-09',
    '2025-07-30': '2025-08-20',
    '2025-09-17': '2025-10-08',
    '2025-10-29': '2025-11-19',
    '2025-12-10': '2025-12-30',
    # 2026
    '2026-01-28': '2026-02-18',
}

# 合并所有数据
ALL_REAL_DATA = {}
ALL_REAL_DATA.update(HISTORICAL_DATA)
ALL_REAL_DATA.update(CALENDAR_DATA)


def build_events() -> list:
    """将真实数据构建为 macro_events 格式的事件列表"""
    events = []
    for meeting_date_str, release_date_str in sorted(ALL_REAL_DATA.items()):
        rd = date.fromisoformat(release_date_str)
        md = date.fromisoformat(meeting_date_str)
        events.append({
            'event_type': 'FOMC_MINUTES',
            'event_date': release_date_str,
            'event_time_utc': f"{release_date_str}T18:00:00Z",
            'year': rd.year,
            'month': rd.month,
            'importance': 'high',
            'description': f'FOMC Minutes (from {meeting_date_str} meeting)',
            'source': 'federalreserve.gov',
            'source_url': 'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',
        })
    return events


def get_old_data():
    """获取数据库中现有的 FOMC_MINUTES 数据用于对比"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT event_date FROM macro_events WHERE event_type='FOMC_MINUTES' ORDER BY event_date")
    old_dates = [row[0] for row in cur.fetchall()]
    conn.close()
    return old_dates


def update_database(events: list):
    """删除旧数据并插入真实数据"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 删除旧的推算数据
    cur.execute("DELETE FROM macro_events WHERE event_type='FOMC_MINUTES'")
    deleted = cur.rowcount
    print(f"  已删除旧的推算数据: {deleted} 条")

    # 插入真实数据
    inserted = 0
    for e in events:
        cur.execute("""
            INSERT INTO macro_events
                (event_type, event_date, event_time_utc, year, month,
                 importance, description, source, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_type, event_date) DO NOTHING
        """, (
            e['event_type'], e['event_date'], e['event_time_utc'],
            e['year'], e['month'], e['importance'],
            e['description'], e['source'], e['source_url'],
        ))
        if cur.rowcount > 0:
            inserted += 1

    conn.commit()
    conn.close()
    print(f"  已插入真实数据: {inserted} 条")
    return deleted, inserted


def update_json_file(json_path: Path, events: list):
    """更新 JSON 文件：删除旧 FOMC_MINUTES，加入新数据"""
    if not json_path.exists():
        print(f"  文件不存在，跳过: {json_path}")
        return

    # 备份
    bak_path = json_path.with_suffix('.json.bak')
    if not bak_path.exists():
        shutil.copy2(json_path, bak_path)
        print(f"  已备份: {bak_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 删除旧的 FOMC_MINUTES
    old_count = len([x for x in data if x.get('event_type') == 'FOMC_MINUTES'])
    data = [x for x in data if x.get('event_type') != 'FOMC_MINUTES']

    # 加入新数据
    data.extend(events)

    # 按 event_date 排序
    data.sort(key=lambda x: (x.get('event_date', ''), x.get('event_type', '')))

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  {json_path.name}: 删除 {old_count} 条旧数据, 加入 {len(events)} 条真实数据")


def print_comparison(old_dates, new_events):
    """对比旧推算数据和新真实数据"""
    old_set = set(d.isoformat() if isinstance(d, date) else d for d in old_dates)
    new_set = set(e['event_date'] for e in new_events)

    only_old = sorted(old_set - new_set)
    only_new = sorted(new_set - old_set)
    common = sorted(old_set & new_set)

    print(f"\n=== 数据对比 ===")
    print(f"旧推算数据: {len(old_set)} 条")
    print(f"新真实数据: {len(new_set)} 条")
    print(f"相同日期:   {len(common)} 条")
    print(f"仅旧数据有: {len(only_old)} 条")
    print(f"仅新数据有: {len(only_new)} 条")

    if only_old:
        print(f"\n旧数据中被移除的日期 (推算不准确):")
        for d in only_old:
            print(f"  - {d}")

    if only_new:
        print(f"\n新增的真实日期:")
        for d in only_new:
            # 找对应的描述
            for e in new_events:
                if e['event_date'] == d:
                    print(f"  + {d}: {e['description']}")
                    break


def main():
    print("=" * 60)
    print("FOMC Minutes 真实发布日期替换脚本")
    print("数据来源: federalreserve.gov")
    print("=" * 60)

    # 1. 构建真实事件数据
    events = build_events()
    print(f"\n真实数据总数: {len(events)} 条")
    print(f"日期范围: {events[0]['event_date']} ~ {events[-1]['event_date']}")

    # 2. 获取旧数据用于对比
    print("\n获取数据库中旧的推算数据...")
    old_dates = get_old_data()
    print(f"  旧数据: {len(old_dates)} 条")

    # 3. 对比
    print_comparison(old_dates, events)

    # 4. 更新数据库
    print(f"\n=== 更新数据库 ===")
    deleted, inserted = update_database(events)

    # 5. 更新 JSON 文件
    data_dir = Path(__file__).parent.parent / 'data'
    print(f"\n=== 更新 JSON 文件 ===")
    update_json_file(data_dir / 'macro_events_fred.json', events)
    update_json_file(data_dir / 'macro_events_all.json', events)

    # 6. 验证
    print(f"\n=== 验证 ===")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT count(*), min(event_date), max(event_date)
        FROM macro_events WHERE event_type='FOMC_MINUTES'
    """)
    row = cur.fetchone()
    print(f"数据库中 FOMC_MINUTES: {row[0]} 条 ({row[1]} ~ {row[2]})")

    # 按年统计
    cur.execute("""
        SELECT year, count(*) FROM macro_events
        WHERE event_type='FOMC_MINUTES'
        GROUP BY year ORDER BY year
    """)
    print("\n按年统计:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} 条")

    # 全表统计
    cur.execute("""
        SELECT event_type, COUNT(*), MIN(event_date), MAX(event_date)
        FROM macro_events GROUP BY event_type ORDER BY event_type
    """)
    print("\n=== 数据库 macro_events 完整统计 ===")
    total = 0
    for row in cur.fetchall():
        print(f"  {row[0]:15s}: {row[1]:4d} 条  ({row[2]} ~ {row[3]})")
        total += row[1]
    print(f"  {'总计':15s}: {total} 条")

    conn.close()
    print("\n完成!")


if __name__ == '__main__':
    main()
