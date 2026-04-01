"""
宏观经济事件内容补充脚本
从 FRED API 获取各指标的真实历史数值，更新 macro_events 表的 description/decision/rate 字段
"""
import sys
import io
import time
from datetime import date, timedelta

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import psycopg2

FRED_KEY = '4a2f776eaba16b7aa835947dbc060a99'
FRED_BASE = 'https://api.stlouisfed.org/fred'


def fred_obs(series_id: str, obs_date: str) -> float | None:
    """获取某序列在指定日期的观测值（realtime当日值）"""
    url = (
        f"{FRED_BASE}/series/observations"
        f"?series_id={series_id}"
        f"&realtime_start={obs_date}"
        f"&realtime_end={obs_date}"
        f"&api_key={FRED_KEY}"
        f"&file_type=json"
        f"&limit=10"
    )
    try:
        r = requests.get(url, timeout=15, proxies={'http': None, 'https': None})
        r.raise_for_status()
        obs = r.json().get('observations', [])
        for o in reversed(obs):
            if o.get('value') not in ('.', '', None):
                return float(o['value'])
    except Exception as e:
        print(f"    FRED obs error ({series_id} @ {obs_date}): {e}")
    return None


def fred_obs_range(series_id: str, start: str, end: str) -> list:
    """获取某序列在日期范围内的所有观测值"""
    url = (
        f"{FRED_BASE}/series/observations"
        f"?series_id={series_id}"
        f"&observation_start={start}"
        f"&observation_end={end}"
        f"&api_key={FRED_KEY}"
        f"&file_type=json"
        f"&limit=1000"
    )
    try:
        r = requests.get(url, timeout=15, proxies={'http': None, 'https': None})
        r.raise_for_status()
        return r.json().get('observations', [])
    except Exception as e:
        print(f"    FRED range error ({series_id}): {e}")
    return []


def update_fomc_rates(conn):
    """更新 FOMC 事件的利率决定"""
    print("\n=== 更新 FOMC 利率 ===")
    cur = conn.cursor()

    # 获取联邦基金利率目标上限完整历史
    print("  获取 DFEDTARU (目标上限)...")
    all_obs = []
    # 分段拉取，每段5年，避免limit截断
    for start_y, end_y in [('2008-01-01', '2013-12-31'), ('2014-01-01', '2019-12-31'), ('2020-01-01', '2026-03-31')]:
        url = (
            f"{FRED_BASE}/series/observations"
            f"?series_id=DFEDTARU"
            f"&observation_start={start_y}"
            f"&observation_end={end_y}"
            f"&api_key={FRED_KEY}"
            f"&file_type=json"
            f"&limit=2000"
        )
        r = requests.get(url, timeout=15, proxies={'http': None, 'https': None})
        r.raise_for_status()
        all_obs.extend(r.json().get('observations', []))
        time.sleep(0.3)
    rate_map = {}
    for o in all_obs:
        if o.get('value') not in ('.', '', None):
            rate_map[o['date']] = float(o['value'])
    print(f"  共获取 {len(rate_map)} 天的利率数据")

    # 获取所有 FOMC 事件
    cur.execute("SELECT id, event_date FROM macro_events WHERE event_type='FOMC' ORDER BY event_date")
    fomc_events = cur.fetchall()

    updated = 0
    prev_rate = None
    for event_id, event_date in fomc_events:
        # 找这个日期或之后最近的利率
        d = event_date
        rate_after = None
        for i in range(10):
            d_str = (d + timedelta(days=i)).isoformat()
            if d_str in rate_map:
                rate_after = rate_map[d_str]
                break

        if rate_after is None:
            # 用前一天的值
            for i in range(1, 30):
                d_str = (d - timedelta(days=i)).isoformat()
                if d_str in rate_map:
                    rate_after = rate_map[d_str]
                    break

        rate_before = prev_rate

        if rate_after is not None:
            if rate_before is None:
                decision = 'hold'
            elif rate_after > rate_before:
                decision = 'hike'
            elif rate_after < rate_before:
                decision = 'cut'
            else:
                decision = 'hold'

            desc = f"FOMC: {decision.upper()} {'%.2f%%' % rate_before if rate_before else 'N/A'} -> {'%.2f%%' % rate_after}"
            cur.execute("""
                UPDATE macro_events SET
                    rate_before=%s, rate_after=%s, decision=%s, description=%s
                WHERE id=%s
            """, (rate_before, rate_after, decision, desc, event_id))
            if cur.rowcount > 0:
                updated += 1
            prev_rate = rate_after

    conn.commit()
    print(f"  更新 {updated}/{len(fomc_events)} 条 FOMC 事件")
    return updated


def update_nfp(conn):
    """更新 NFP 事件：新增就业人数 + 失业率"""
    print("\n=== 更新 NFP ===")
    cur = conn.cursor()

    # 获取完整序列
    payems = {o['date']: o['value'] for o in fred_obs_range('PAYEMS', '2012-01-01', '2026-03-31') if o.get('value') not in ('.', None)}
    unrate = {o['date']: o['value'] for o in fred_obs_range('UNRATE', '2012-01-01', '2026-03-31') if o.get('value') not in ('.', None)}
    time.sleep(0.5)

    cur.execute("SELECT id, event_date FROM macro_events WHERE event_type='NFP' ORDER BY event_date")
    events = cur.fetchall()

    updated = 0
    sorted_payems_dates = sorted(payems.keys())

    for event_id, event_date in events:
        d_str = event_date.isoformat()
        # NFP 报告的是上个月数据，找最近可用的 PAYEMS 值
        emp = None
        emp_prev = None
        for pd in sorted_payems_dates:
            if pd <= d_str:
                if emp is not None:
                    emp_prev = emp
                emp = payems[pd]

        rate = None
        for pd in sorted(unrate.keys()):
            if pd <= d_str:
                rate = unrate[pd]

        if emp:
            # 计算月增量（千人）
            change = None
            if emp_prev:
                change = round(float(emp) - float(emp_prev), 0)
            rate_str = f", unemployment {rate}%" if rate else ""
            change_str = f"+{int(change)}K" if change and change >= 0 else (f"{int(change)}K" if change else "N/A")
            desc = f"NFP: {change_str} jobs{rate_str}"
            cur.execute("UPDATE macro_events SET description=%s WHERE id=%s", (desc, event_id))
            if cur.rowcount > 0:
                updated += 1

    conn.commit()
    print(f"  更新 {updated}/{len(events)} 条 NFP 事件")
    return updated


def update_cpi(conn):
    """更新 CPI 事件"""
    print("\n=== 更新 CPI ===")
    cur = conn.cursor()

    cpiaucsl = {o['date']: float(o['value']) for o in fred_obs_range('CPIAUCSL', '2012-01-01', '2026-03-31') if o.get('value') not in ('.', None)}
    time.sleep(0.5)

    cur.execute("SELECT id, event_date FROM macro_events WHERE event_type='CPI' ORDER BY event_date")
    events = cur.fetchall()

    updated = 0
    sorted_dates = sorted(cpiaucsl.keys())

    for event_id, event_date in events:
        d_str = event_date.isoformat()
        # 找最近的 CPI 值和12个月前的值计算同比
        curr_val = None
        prev_val = None
        for pd in sorted_dates:
            if pd <= d_str:
                curr_date = pd
                curr_val = cpiaucsl[pd]
        if curr_val:
            # 找12个月前的值
            prev_target = curr_date[:4] + '-' + str(int(curr_date[5:7]) - 12 // 12).zfill(2) + curr_date[7:] if False else None
            # 简单：找12个月前最近的值
            curr_dt = date.fromisoformat(curr_date)
            prev_dt_str = date(curr_dt.year - 1, curr_dt.month, 1).isoformat()
            for pd in sorted_dates:
                if pd >= prev_dt_str and pd <= (date(curr_dt.year - 1, curr_dt.month, 28)).isoformat():
                    prev_val = cpiaucsl[pd]
                    break

            if prev_val and prev_val > 0:
                yoy = round((curr_val - prev_val) / prev_val * 100, 1)
                desc = f"CPI: {curr_val:.1f}, YoY: {yoy:+.1f}%"
            else:
                desc = f"CPI: {curr_val:.1f}"

            cur.execute("UPDATE macro_events SET description=%s WHERE id=%s", (desc, event_id))
            if cur.rowcount > 0:
                updated += 1

    conn.commit()
    print(f"  更新 {updated}/{len(events)} 条 CPI 事件")
    return updated


def update_ppi(conn):
    """更新 PPI 事件"""
    print("\n=== 更新 PPI ===")
    cur = conn.cursor()

    ppiaco = {o['date']: float(o['value']) for o in fred_obs_range('PPIACO', '2012-01-01', '2026-03-31') if o.get('value') not in ('.', None)}
    time.sleep(0.5)

    cur.execute("SELECT id, event_date FROM macro_events WHERE event_type='PPI' ORDER BY event_date")
    events = cur.fetchall()

    updated = 0
    sorted_dates = sorted(ppiaco.keys())
    prev_val = None

    for event_id, event_date in events:
        d_str = event_date.isoformat()
        curr_val = None
        for pd in sorted_dates:
            if pd <= d_str:
                curr_val = ppiaco[pd]

        if curr_val:
            if prev_val and prev_val > 0:
                mom = round((curr_val - prev_val) / prev_val * 100, 2)
                desc = f"PPI: {curr_val:.1f}, MoM: {mom:+.2f}%"
            else:
                desc = f"PPI: {curr_val:.1f}"
            prev_val = curr_val
            cur.execute("UPDATE macro_events SET description=%s WHERE id=%s", (desc, event_id))
            if cur.rowcount > 0:
                updated += 1

    conn.commit()
    print(f"  更新 {updated}/{len(events)} 条 PPI 事件")
    return updated


def update_gdp(conn):
    """更新 GDP 事件"""
    print("\n=== 更新 GDP ===")
    cur = conn.cursor()

    # A191RL1Q225SBEA = 实际GDP增长率（季度年化）
    gdp_growth = {o['date']: float(o['value']) for o in fred_obs_range('A191RL1Q225SBEA', '2012-01-01', '2026-03-31') if o.get('value') not in ('.', None)}
    time.sleep(0.5)

    cur.execute("SELECT id, event_date FROM macro_events WHERE event_type='GDP' ORDER BY event_date")
    events = cur.fetchall()

    updated = 0
    sorted_dates = sorted(gdp_growth.keys())

    for event_id, event_date in events:
        d_str = event_date.isoformat()
        val = None
        for pd in sorted_dates:
            if pd <= d_str:
                val = gdp_growth[pd]

        if val is not None:
            desc = f"GDP Growth: {val:+.1f}% (annualized, real)"
            cur.execute("UPDATE macro_events SET description=%s WHERE id=%s", (desc, event_id))
            if cur.rowcount > 0:
                updated += 1

    conn.commit()
    print(f"  更新 {updated}/{len(events)} 条 GDP 事件")
    return updated


def update_pce(conn):
    """更新 PCE 事件"""
    print("\n=== 更新 PCE ===")
    cur = conn.cursor()

    # PCEPILFE = 核心PCE价格指数
    pce_core = {o['date']: float(o['value']) for o in fred_obs_range('PCEPILFE', '2012-01-01', '2026-03-31') if o.get('value') not in ('.', None)}
    time.sleep(0.5)

    cur.execute("SELECT id, event_date FROM macro_events WHERE event_type='PCE' ORDER BY event_date")
    events = cur.fetchall()

    updated = 0
    sorted_dates = sorted(pce_core.keys())

    for event_id, event_date in events:
        d_str = event_date.isoformat()
        curr_val = None
        curr_date = None
        for pd in sorted_dates:
            if pd <= d_str:
                curr_val = pce_core[pd]
                curr_date = pd

        if curr_val and curr_date:
            curr_dt = date.fromisoformat(curr_date)
            prev_val = None
            for pd in sorted_dates:
                if pd >= date(curr_dt.year - 1, curr_dt.month, 1).isoformat() and \
                   pd <= date(curr_dt.year - 1, curr_dt.month, 28).isoformat():
                    prev_val = pce_core[pd]
                    break

            if prev_val and prev_val > 0:
                yoy = round((curr_val - prev_val) / prev_val * 100, 1)
                desc = f"Core PCE: {curr_val:.1f}, YoY: {yoy:+.1f}%"
            else:
                desc = f"Core PCE: {curr_val:.1f}"

            cur.execute("UPDATE macro_events SET description=%s WHERE id=%s", (desc, event_id))
            if cur.rowcount > 0:
                updated += 1

    conn.commit()
    print(f"  更新 {updated}/{len(events)} 条 PCE 事件")
    return updated


def main():
    conn = psycopg2.connect(
        host='localhost', port=5432, database='quant_trading',
        user='postgres', password='@Cmx1454697261'
    )

    total = 0
    total += update_fomc_rates(conn)
    total += update_nfp(conn)
    total += update_cpi(conn)
    total += update_ppi(conn)
    total += update_gdp(conn)
    total += update_pce(conn)

    print(f"\n总计更新 {total} 条")

    # 验证样本
    cur = conn.cursor()
    print("\n=== 验证样本 ===")
    for etype in ['FOMC', 'NFP', 'CPI', 'PPI', 'GDP', 'PCE']:
        cur.execute("SELECT event_date, description, decision, rate_before, rate_after FROM macro_events WHERE event_type=%s AND description IS NOT NULL ORDER BY event_date DESC LIMIT 1", (etype,))
        row = cur.fetchone()
        if row:
            print(f"  {etype}: {row[0]} | {row[1]} | decision={row[2]} rate={row[3]}->{row[4]}")
    conn.close()


if __name__ == '__main__':
    main()
