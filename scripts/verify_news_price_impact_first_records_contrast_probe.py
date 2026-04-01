#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small contrast probe for early records in verify_news_price_impact main loop.

Purpose:
- Inspect only a tiny prefix of records (default 5)
- Identify the first record that enters symbol/minute-price path and whether any stage becomes slow
- Keep per-stage statement timeout and immediate log flush
"""
from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
TS = datetime.now().strftime('%Y%m%d-%H%M%S')
LOG_PATH = LOG_DIR / f'verify_news_price_impact_first_records_contrast_probe_{TS}.log'


def log(fh, stage: str, status: str, detail: str = '') -> None:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] stage={stage} status={status}'
    if detail:
        line += f' detail={detail}'
    fh.write(line + '\n')
    fh.flush()
    os.fsync(fh.fileno())


def set_statement_timeout(cur, timeout_ms: int) -> None:
    cur.execute(f'SET statement_timeout TO {int(timeout_ms)}')


def main() -> int:
    with open(LOG_PATH, 'a', encoding='utf-8', buffering=1) as fh:
        log(fh, 'probe', 'INFO', f'log_path={LOG_PATH}')
        log(fh, 'probe', 'INFO', 'limit=5')
        try:
            import importlib
            from datetime import timedelta
            mod = importlib.import_module('scripts.verify_news_price_impact')
            conn = mod.get_connection()
            conn.autocommit = True
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            try:
                anchor_expr = """
                    COALESCE(na.effective_time, na.analyzed_at, na.published_time, nr.time)
                """
                set_statement_timeout(cur, 30000)
                cur.execute(f"""
                    SELECT na.id, na.news_id,
                           {anchor_expr} AS anchor_time,
                           na.published_time,
                           na.analyzed_at,
                           na.effective_time,
                           nr.time AS news_time,
                           na.direction,
                           na.importance,
                           na.confidence,
                           nr.title
                    FROM news_analysis na
                    JOIN news_raw nr ON na.news_id = nr.id
                    ORDER BY {anchor_expr}
                    LIMIT 5
                """)
                records = cur.fetchall()
                log(fh, 'records_loaded', 'INFO', f'count={len(records)}')

                for idx, rec in enumerate(records, 1):
                    rid = rec['id']
                    anchor_ts = rec['anchor_time']
                    log(fh, 'record', 'INFO', f'idx={idx} id={rid} anchor_time={anchor_ts} news_time={rec["news_time"]} direction={rec["direction"]}')
                    set_statement_timeout(cur, 5000)
                    symbol = mod.find_best_symbol(cur, anchor_ts)
                    log(fh, 'find_best_symbol', 'INFO', f'idx={idx} id={rid} symbol={symbol}')
                    if symbol:
                        set_statement_timeout(cur, 5000)
                        base_price, base_time = mod.find_price(cur, symbol, anchor_ts, direction='nearest')
                        log(fh, 'find_price_base', 'INFO', f'idx={idx} id={rid} symbol={symbol} base_price={base_price} base_time={base_time}')
                        set_statement_timeout(cur, 5000)
                        price_30m, time_30m = mod.find_price(cur, symbol, anchor_ts + timedelta(minutes=30), direction='after')
                        log(fh, 'find_price_30m', 'INFO', f'idx={idx} id={rid} price_30m={price_30m} time_30m={time_30m}')
                        log(fh, 'probe', 'RESULT', f'first_symbol_record_idx={idx} id={rid}')
                        return 0
                log(fh, 'probe', 'RESULT', 'no_symbol_in_first_5_records')
                return 0
            finally:
                cur.close()
                conn.close()
                log(fh, 'db_connection', 'INFO', 'closed')
        except Exception:
            log(fh, 'probe', 'TRACEBACK', traceback.format_exc().replace('\n', ' | '))
            return 1


if __name__ == '__main__':
    raise SystemExit(main())
