#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Early blocking probe for scripts/verify_news_price_impact.py dry-run startup path.

Purpose:
- Locate the first blocking stage conservatively
- Write one line per stage to a dedicated probe log file with immediate flush
- Apply per-stage timeouts / DB statement timeouts
- Stop once the first blocking stage is identified

This is a standalone probe script to avoid expanding scope in business logic.
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
TS = datetime.now().strftime('%Y%m%d-%H%M%S')
LOG_PATH = LOG_DIR / f'verify_news_price_impact_early_probe_{TS}.log'


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
    except Exception as exc:  # pragma: no cover - probe path
        elapsed = time.monotonic() - start
        logger.log(stage, 'ERROR', f'elapsed_s={elapsed:.3f}; exc={type(exc).__name__}: {exc}')
        raise
    else:
        elapsed = time.monotonic() - start
        logger.log(stage, 'OK', f'elapsed_s={elapsed:.3f}')


def main() -> int:
    logger = ProbeLogger(LOG_PATH)
    logger.log('probe', 'INFO', f'log_path={LOG_PATH}')
    logger.log('probe', 'INFO', f'python={sys.executable}')
    logger.log('probe', 'INFO', f'cwd={os.getcwd()}')
    logger.log('probe', 'INFO', 'strategy=standalone_early_block_probe')

    try:
        with timed_stage(logger, 'import_module_complete', 60):
            import importlib
            mod = importlib.import_module('scripts.verify_news_price_impact')

        with timed_stage(logger, 'config_env_loaded', 60):
            db_conf = mod.DB_CONFIG
            safe_detail = f"host={db_conf.get('host')} port={db_conf.get('port')} dbname={db_conf.get('dbname')} user={db_conf.get('user')}"
            logger.log('config_env_loaded', 'INFO', safe_detail)

        with timed_stage(logger, 'db_connect_before', 30):
            pass

        with timed_stage(logger, 'db_connect_after', 30):
            conn = mod.get_connection()
            conn.autocommit = True

        try:
            with timed_stage(logger, 'select_1_before', 20):
                pass

            with timed_stage(logger, 'select_1_after', 20):
                cur = conn.cursor()
                cur.execute('SET statement_timeout TO 20000')
                cur.execute('SELECT 1')
                row = cur.fetchone()
                logger.log('select_1_after', 'INFO', f'result={row}')
                cur.close()

            with timed_stage(logger, 'news_analysis_sample_before', 45):
                pass

            with timed_stage(logger, 'news_analysis_sample_after', 45):
                cur = conn.cursor()
                cur.execute('SET statement_timeout TO 45000')
                cur.execute(
                    """
                    SELECT na.id, na.news_id,
                           COALESCE(na.effective_time, na.analyzed_at, na.published_time, nr.time) AS anchor_time,
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
                    ORDER BY COALESCE(na.effective_time, na.analyzed_at, na.published_time, nr.time)
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                logger.log('news_analysis_sample_after', 'INFO', f'row_found={row is not None}')
                cur.close()

            with timed_stage(logger, 'before_main_loop', 20):
                cur = conn.cursor()
                cur.execute('SET statement_timeout TO 20000')
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM news_analysis na
                    JOIN news_raw nr ON na.news_id = nr.id
                    """
                )
                total = cur.fetchone()[0]
                logger.log('before_main_loop', 'INFO', f'total_records={total}')
                cur.close()
        finally:
            conn.close()
            logger.log('db_connection', 'INFO', 'closed')

        logger.log('probe', 'RESULT', 'all_requested_probe_points_reached')
        return 0
    except Exception:  # pragma: no cover - probe path
        logger.log('probe', 'TRACEBACK', traceback.format_exc().replace('\n', ' | '))
        return 1
    finally:
        logger.close()


if __name__ == '__main__':
    raise SystemExit(main())
