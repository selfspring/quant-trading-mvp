#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""First-record probe for scripts/verify_news_price_impact.py main-loop path.

Purpose:
- Probe only the first record in the main loop path
- Write one line per stage to a dedicated log file with immediate flush
- Apply per-stage DB statement timeout guards
- Stop once the first slow/blocking stage is identified

This is a standalone probe script to avoid modifying production business logic.
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
TS = datetime.now().strftime('%Y%m%d-%H%M%S')
LOG_PATH = LOG_DIR / f'verify_news_price_impact_first_record_probe_{TS}.log'


class ProbeLogger:
    def __init__(self, path: Path):
        self.path = path
        self._fh = open(path, 'a', encoding='utf-8', buffering=1)

    def log(self, stage: str, status: str, detail: str = '') -> None:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f'[{ts}] stage={stage} status={status}'
        if detail:
            line += f' detail={detail}'
        self._fh.write(line + '\n')
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def close(self) -> None:
        self._fh.close()


@contextmanager
def timed_stage(logger: ProbeLogger, stage: str, timeout_s: int):
    start = time.monotonic()
    logger.log(stage, 'START', f'timeout_s={timeout_s}')
    try:
        yield
    except Exception as exc:
        elapsed = time.monotonic() - start
        logger.log(stage, 'ERROR', f'elapsed_s={elapsed:.3f}; exc={type(exc).__name__}: {exc}')
        raise
    else:
        elapsed = time.monotonic() - start
        logger.log(stage, 'OK', f'elapsed_s={elapsed:.3f}')


def set_statement_timeout(cur, timeout_ms: int) -> None:
    cur.execute(f'SET statement_timeout TO {int(timeout_ms)}')


def compact_record(rec) -> str:
    title = rec['title'] or ''
    title = title.replace('\r', ' ').replace('\n', ' ').strip()
    if len(title) > 80:
        title = title[:77] + '...'
    return (
        f"id={rec['id']} news_id={rec['news_id']} anchor_time={rec['anchor_time']} "
        f"published_time={rec['published_time']} analyzed_at={rec['analyzed_at']} "
        f"effective_time={rec['effective_time']} news_time={rec['news_time']} "
        f"direction={rec['direction']} importance={rec['importance']} confidence={rec['confidence']} "
        f"title={title!r}"
    )


def main() -> int:
    logger = ProbeLogger(LOG_PATH)
    logger.log('probe', 'INFO', f'log_path={LOG_PATH}')
    logger.log('probe', 'INFO', f'python={sys.executable}')
    logger.log('probe', 'INFO', f'cwd={os.getcwd()}')
    logger.log('probe', 'INFO', 'strategy=standalone_first_record_main_loop_probe')

    try:
        import importlib
        mod = importlib.import_module('scripts.verify_news_price_impact')

        conn = mod.get_connection()
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            anchor_expr = """
                COALESCE(na.effective_time, na.analyzed_at, na.published_time, nr.time)
            """

            with timed_stage(logger, 'records_fetched', 60):
                set_statement_timeout(cur, 60000)
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
                """)
                records = cur.fetchall()
                logger.log('records_fetched', 'INFO', f'total_records={len(records)}')
                if not records:
                    logger.log('probe', 'RESULT', 'no_records_found')
                    return 0

            first = records[0]
            logger.log('loop_record_picked', 'INFO', compact_record(first))

            anchor_ts = first['anchor_time']
            if anchor_ts is None:
                logger.log('loop_record_picked', 'WARN', 'anchor_time_is_null')
                logger.log('probe', 'RESULT', 'first_record_anchor_time_null')
                return 0

            with timed_stage(logger, 'find_best_symbol_before', 1):
                pass

            with timed_stage(logger, 'find_best_symbol_after', 30):
                set_statement_timeout(cur, 30000)
                symbol = mod.find_best_symbol(cur, anchor_ts)
                logger.log('find_best_symbol_after', 'INFO', f'symbol={symbol}')

            base_price = None
            base_time = None
            if symbol:
                with timed_stage(logger, 'base_price_lookup_before', 1):
                    pass

                with timed_stage(logger, 'base_price_lookup_after', 30):
                    set_statement_timeout(cur, 30000)
                    base_price, base_time = mod.find_price(cur, symbol, anchor_ts, direction='nearest')
                    logger.log('base_price_lookup_after', 'INFO', f'base_price={base_price} base_time={base_time} symbol={symbol}')
            else:
                logger.log('base_price_lookup_after', 'INFO', 'skip_find_price_due_to_no_symbol')

            if base_price is None:
                with timed_stage(logger, 'daily_base_price_fallback_before', 1):
                    pass

                with timed_stage(logger, 'daily_base_price_fallback_after', 30):
                    set_statement_timeout(cur, 30000)
                    base_price, base_time = mod.find_daily_base_price(cur, anchor_ts)
                    logger.log('daily_base_price_fallback_after', 'INFO', f'base_price={base_price} base_time={base_time}')

            if base_price is None:
                logger.log('probe', 'RESULT', 'first_record_no_base_price')
                return 0

            if symbol:
                with timed_stage(logger, 'price_30m_lookup_before', 1):
                    pass

                with timed_stage(logger, 'price_30m_lookup_after', 30):
                    set_statement_timeout(cur, 30000)
                    price_30m, time_30m = mod.find_price(cur, symbol, anchor_ts + timedelta(minutes=30), direction='after')
                    logger.log('price_30m_lookup_after', 'INFO', f'price_30m={price_30m} time_30m={time_30m}')

                with timed_stage(logger, 'price_4h_lookup_before', 1):
                    pass

                with timed_stage(logger, 'price_4h_lookup_after', 30):
                    set_statement_timeout(cur, 30000)
                    price_4h, time_4h = mod.find_price(cur, symbol, anchor_ts + timedelta(hours=4), direction='after')
                    logger.log('price_4h_lookup_after', 'INFO', f'price_4h={price_4h} time_4h={time_4h}')
            else:
                logger.log('price_30m_lookup_after', 'INFO', 'skip_due_to_daily_symbol_fallback')
                logger.log('price_4h_lookup_after', 'INFO', 'skip_due_to_daily_symbol_fallback')

            with timed_stage(logger, 'price_1d_lookup_before', 1):
                pass

            with timed_stage(logger, 'price_1d_lookup_after', 30):
                set_statement_timeout(cur, 30000)
                price_1d, date_1d = mod.find_daily_price_1d(cur, anchor_ts)
                logger.log('price_1d_lookup_after', 'INFO', f'price_1d={price_1d} date_1d={date_1d}')

            logger.log('probe', 'RESULT', 'all_first_record_probe_points_reached')
            return 0
        finally:
            cur.close()
            conn.close()
            logger.log('db_connection', 'INFO', 'closed')
    except Exception:
        logger.log('probe', 'TRACEBACK', traceback.format_exc().replace('\n', ' | '))
        return 1
    finally:
        logger.close()


if __name__ == '__main__':
    raise SystemExit(main())
