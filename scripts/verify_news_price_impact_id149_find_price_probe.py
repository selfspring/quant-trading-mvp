#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused probe for analysis_id/id=149 find_price() path.

Purpose:
- Probe only news_analysis.id=149
- Keep per-query statement_timeout boundaries (3~5s)
- Log each sub-step of find_best_symbol / find_price_base / 30m / 4h / 1d
- Stop after identifying first real timeout or first significant slow point

Standalone script; does not modify production business logic.
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
TS = datetime.now().strftime('%Y%m%d-%H%M%S')
LOG_PATH = LOG_DIR / f'verify_news_price_impact_id149_find_price_probe_{TS}.log'
TARGET_ID = 149
SIGNIFICANT_SLOW_MS = 500


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
def stage(logger: ProbeLogger, stage_name: str, detail: str = ''):
    start = time.monotonic()
    logger.log(stage_name, 'START', detail)
    try:
        yield start
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.log(stage_name, 'ERROR', f'elapsed_ms={elapsed_ms:.1f}; exc={type(exc).__name__}: {exc}')
        raise
    else:
        elapsed_ms = (time.monotonic() - start) * 1000
        level = 'SLOW' if elapsed_ms >= SIGNIFICANT_SLOW_MS else 'OK'
        logger.log(stage_name, level, f'elapsed_ms={elapsed_ms:.1f}')


def set_statement_timeout(cur, timeout_ms: int) -> None:
    cur.execute(f'SET statement_timeout TO {int(timeout_ms)}')


def fetchone_timed(logger, cur, stage_name: str, sql: str, params, timeout_ms: int, meta: str):
    with stage(logger, stage_name, f'timeout_ms={timeout_ms}; {meta}'):
        set_statement_timeout(cur, timeout_ms)
        cur.execute(sql, params)
        row = cur.fetchone()
        logger.log(stage_name, 'INFO', f'hit={row is not None}; row={row}')
        return row


def fetchall_timed(logger, cur, stage_name: str, sql: str, params, timeout_ms: int, meta: str):
    with stage(logger, stage_name, f'timeout_ms={timeout_ms}; {meta}'):
        set_statement_timeout(cur, timeout_ms)
        cur.execute(sql, params)
        rows = cur.fetchall()
        logger.log(stage_name, 'INFO', f'rows={rows}')
        return rows


def compact_record(rec) -> str:
    title = rec['title'] or ''
    title = title.replace('\r', ' ').replace('\n', ' ').strip()
    if len(title) > 120:
        title = title[:117] + '...'
    return (
        f"id={rec['id']} news_id={rec['news_id']} anchor_time={rec['anchor_time']} "
        f"published_time={rec['published_time']} analyzed_at={rec['analyzed_at']} "
        f"effective_time={rec['effective_time']} news_time={rec['news_time']} "
        f"direction={rec['direction']} importance={rec['importance']} confidence={rec['confidence']} "
        f"title={title!r}"
    )


def run() -> int:
    logger = ProbeLogger(LOG_PATH)
    logger.log('probe', 'INFO', f'log_path={LOG_PATH}')
    logger.log('probe', 'INFO', f'target_id={TARGET_ID}')
    logger.log('probe', 'INFO', f'python={sys.executable}')
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
            sql_record = f"""
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
                WHERE na.id = %s
            """
            with stage(logger, 'record_load', 'load id=149 core fields'):
                set_statement_timeout(cur, 5000)
                cur.execute(sql_record, (TARGET_ID,))
                rec = cur.fetchone()
                logger.log('record_load', 'INFO', compact_record(rec) if rec else 'not_found')
            if not rec:
                logger.log('probe', 'RESULT', 'record_not_found')
                return 1

            anchor_ts = rec['anchor_time']
            logger.log('record_key_fields', 'INFO', f'analysis_id={rec["id"]}; symbol_hint=au9999; anchor_time={anchor_ts}; news_time={rec["news_time"]}')

            window_start = anchor_ts - timedelta(days=1)
            window_end = anchor_ts + timedelta(days=2)
            preferred = ('au_continuous', 'au9999', 'au2606', 'au_main')

            rows_30m = fetchall_timed(
                logger, cur, 'find_best_symbol_30m_window',
                """
                SELECT symbol, COUNT(*) as cnt
                FROM kline_data
                WHERE time >= %s AND time <= %s
                  AND symbol IN ('au_continuous', 'au9999', 'au2606', 'au_main')
                  AND interval = '30m'
                GROUP BY symbol
                ORDER BY cnt DESC
                """,
                (window_start, window_end), 5000,
                f'table=kline_data; interval=30m; window_start={window_start}; window_end={window_end}'
            )

            rows_all = None
            if not rows_30m:
                rows_all = fetchall_timed(
                    logger, cur, 'find_best_symbol_all_interval_window',
                    """
                    SELECT symbol, COUNT(*) as cnt
                    FROM kline_data
                    WHERE time >= %s AND time <= %s
                      AND symbol IN ('au_continuous', 'au9999', 'au2606', 'au_main')
                    GROUP BY symbol
                    ORDER BY cnt DESC
                    """,
                    (window_start, window_end), 5000,
                    f'table=kline_data; interval=ALL; window_start={window_start}; window_end={window_end}'
                )

            with stage(logger, 'find_best_symbol_select', 'apply preferred order threshold'):
                source_rows = rows_30m or rows_all or []
                symbol = None
                if source_rows:
                    best_count = source_rows[0][1]
                    for sym in ['au_main', 'au_continuous', 'au2606', 'au9999']:
                        for row in source_rows:
                            if row[0] == sym and row[1] >= best_count * 0.3:
                                symbol = sym
                                break
                        if symbol:
                            break
                    if symbol is None:
                        symbol = source_rows[0][0]
                logger.log('find_best_symbol_select', 'INFO', f'symbol={symbol}; source_rows={source_rows}')

            if not symbol:
                logger.log('probe', 'RESULT', 'no_symbol_found_for_id149')
                return 0

            def probe_find_price(label: str, target_time, direction: str):
                logger.log(label, 'INFO', f'enter target_time={target_time}; direction={direction}; symbol={symbol}')
                interval_priority = ['30m', '1m', '15m', None]
                for interval in interval_priority:
                    interval_name = interval or 'ALL'
                    row_before = None
                    row_after = None

                    if direction in ('before', 'nearest'):
                        sql_before = """
                            SELECT close, time FROM kline_data
                            WHERE symbol = %s AND time <= %s AND interval = %s
                            ORDER BY time DESC LIMIT 1
                        """ if interval else """
                            SELECT close, time FROM kline_data
                            WHERE symbol = %s AND time <= %s
                            ORDER BY time DESC LIMIT 1
                        """
                        params_before = (symbol, target_time, interval) if interval else (symbol, target_time)
                        try:
                            row_before = fetchone_timed(
                                logger, cur, f'{label}_{interval_name}_before_query',
                                sql_before, params_before, 5000,
                                f'table=kline_data; symbol={symbol}; interval={interval_name}; direction_part=before; target_time={target_time}'
                            )
                        except psycopg2.errors.QueryCanceled as exc:
                            logger.log(label, 'TIMEOUT', f'first_timeout_stage={label}_{interval_name}_before_query; exc={exc}')
                            raise

                    if direction in ('after', 'nearest'):
                        sql_after = """
                            SELECT close, time FROM kline_data
                            WHERE symbol = %s AND time >= %s AND interval = %s
                            ORDER BY time ASC LIMIT 1
                        """ if interval else """
                            SELECT close, time FROM kline_data
                            WHERE symbol = %s AND time >= %s
                            ORDER BY time ASC LIMIT 1
                        """
                        params_after = (symbol, target_time, interval) if interval else (symbol, target_time)
                        try:
                            row_after = fetchone_timed(
                                logger, cur, f'{label}_{interval_name}_after_query',
                                sql_after, params_after, 5000,
                                f'table=kline_data; symbol={symbol}; interval={interval_name}; direction_part=after; target_time={target_time}'
                            )
                        except psycopg2.errors.QueryCanceled as exc:
                            logger.log(label, 'TIMEOUT', f'first_timeout_stage={label}_{interval_name}_after_query; exc={exc}')
                            raise

                    if direction == 'nearest':
                        if row_before and row_after:
                            diff_b = abs((target_time - row_before[1]).total_seconds())
                            diff_a = abs((row_after[1] - target_time).total_seconds())
                            row = row_before if diff_b <= diff_a else row_after
                            logger.log(label, 'INFO', f'interval={interval_name}; choose=before' if diff_b <= diff_a else f'interval={interval_name}; choose=after')
                        elif row_before:
                            row = row_before
                            logger.log(label, 'INFO', f'interval={interval_name}; choose=before_only')
                        elif row_after:
                            row = row_after
                            logger.log(label, 'INFO', f'interval={interval_name}; choose=after_only')
                        else:
                            row = None
                            logger.log(label, 'INFO', f'interval={interval_name}; no_row')
                    elif direction == 'before':
                        row = row_before
                    else:
                        row = row_after

                    if row is None:
                        continue

                    gap_s = abs((row[1] - target_time).total_seconds())
                    logger.log(label, 'INFO', f'interval={interval_name}; hit_price={float(row[0])}; hit_time={row[1]}; gap_s={gap_s}')
                    if gap_s > 5 * 24 * 3600:
                        logger.log(label, 'WARN', f'interval={interval_name}; reject_due_to_gap_s={gap_s}')
                        continue
                    return float(row[0]), row[1], interval_name

                return None, None, None

            first_timeout = None
            first_significant = None

            def guarded_probe(label, target_time, direction):
                nonlocal first_timeout, first_significant
                stage_start = time.monotonic()
                try:
                    price, hit_time, used_interval = probe_find_price(label, target_time, direction)
                except psycopg2.errors.QueryCanceled:
                    first_timeout = label
                    logger.log('probe', 'RESULT', f'first_real_timeout={label}')
                    return 'timeout', None, None, None
                elapsed_ms = (time.monotonic() - stage_start) * 1000
                logger.log(label, 'INFO', f'completed elapsed_ms={elapsed_ms:.1f}; price={price}; hit_time={hit_time}; used_interval={used_interval}')
                if first_significant is None and elapsed_ms >= SIGNIFICANT_SLOW_MS:
                    first_significant = (label, elapsed_ms)
                    logger.log('probe', 'INFO', f'first_significant_slow_point={label}; elapsed_ms={elapsed_ms:.1f}')
                return 'ok', price, hit_time, used_interval

            status, base_price, base_time, base_interval = guarded_probe('find_price_base', anchor_ts, 'nearest')
            if status == 'timeout':
                return 0

            status, price_30m, time_30m, interval_30m = guarded_probe('find_price_30m', anchor_ts + timedelta(minutes=30), 'after')
            if status == 'timeout':
                return 0

            status_4h, price_4h, time_4h, interval_4h = guarded_probe('find_price_4h', anchor_ts + timedelta(hours=4), 'after')
            if status_4h == 'timeout':
                return 0

            row_daily = fetchone_timed(
                logger, cur, 'find_price_1d_daily_query',
                """
                SELECT close, time FROM kline_daily
                WHERE symbol = 'au_continuous' AND time > %s
                ORDER BY time ASC LIMIT 1
                """,
                (anchor_ts.date(),), 5000,
                f'table=kline_daily; symbol=au_continuous; direction_part=after; target_date={anchor_ts.date()}'
            )
            if row_daily:
                logger.log('find_price_1d', 'INFO', f'price={float(row_daily[0])}; date={row_daily[1]}')
            else:
                logger.log('find_price_1d', 'INFO', 'no_row')

            logger.log('probe_summary', 'INFO', (
                f'symbol={symbol}; base_price={base_price}; base_time={base_time}; base_interval={base_interval}; '
                f'price_30m={price_30m}; time_30m={time_30m}; interval_30m={interval_30m}; '
                f'price_4h={price_4h}; time_4h={time_4h}; interval_4h={interval_4h}; '
                f'price_1d={float(row_daily[0]) if row_daily else None}; date_1d={row_daily[1] if row_daily else None}; '
                f'first_timeout={first_timeout}; first_significant={first_significant}'
            ))
            logger.log('probe', 'RESULT', f'completed_without_timeout; first_significant={first_significant}')
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
    raise SystemExit(run())
