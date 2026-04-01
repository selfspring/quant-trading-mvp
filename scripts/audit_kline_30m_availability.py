#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sample-level 30m availability / lineage audit.

用途：
- 对少量样本 bucket 输出/写入 availability 状态
- 证明“能合并 / 不能合并则标注”的最小逻辑已可运行

默认样本：
- au9999@2012-12-31 09:00:00+08 -> 预期 MERGEABLE_FROM_1M（有完整 1m，无原生 30m）
- au9999@2013-01-02 18:30:00+08 -> 预期 NOT_MERGEABLE_CROSS_SESSION（夜盘关闭窗口）
- au9999@2012-12-31 10:00:00+08 -> 预期 NOT_MERGEABLE_1M_GAP（10:15-10:30 休市导致跨段）
- au9999@2013-01-02 09:00:00+08 -> 预期 NOT_MERGEABLE_NO_1M（交易时段内无 1m）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.common.config import config
from quant.common.db import db_connection
from quant.common.kline_availability import (
    RULE_VERSION,
    AvailabilityEvaluation,
    evaluate_bucket,
    floor_to_30m_bucket,
)

TZ = ZoneInfo('Asia/Shanghai')
DEFAULT_SAMPLES = [
    ('au9999', '2012-12-31T09:00:00+08:00'),
    ('au9999', '2013-01-02T18:30:00+08:00'),
    ('au9999', '2012-12-31T10:00:00+08:00'),
    ('au9999', '2013-01-02T09:00:00+08:00'),
]


def parse_sample(value: str) -> tuple[str, datetime]:
    symbol, ts = value.split('@', 1)
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return symbol, floor_to_30m_bucket(dt)


def _load_bucket_inputs(symbol: str, bucket_start: datetime) -> tuple[bool, list[datetime]]:
    bucket_end = bucket_start.replace(second=0, microsecond=0)
    with db_connection(config) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT EXISTS(
                SELECT 1
                FROM kline_data
                WHERE symbol = %s AND interval = '30m' AND time = %s
            )
            """,
            (symbol, bucket_start),
        )
        native_exists = bool(cur.fetchone()[0])

        cur.execute(
            """
            SELECT time
            FROM kline_data
            WHERE symbol = %s
              AND interval = '1m'
              AND time >= %s
              AND time < %s + INTERVAL '30 minutes'
            ORDER BY time ASC
            """,
            (symbol, bucket_start, bucket_start),
        )
        minute_rows = [row[0] for row in cur.fetchall()]
        cur.close()
    return native_exists, minute_rows


def evaluate_sample(symbol: str, bucket_start: datetime) -> AvailabilityEvaluation:
    native_exists, minute_rows = _load_bucket_inputs(symbol, bucket_start)
    return evaluate_bucket(
        symbol=symbol,
        bucket_start=bucket_start,
        native_30m_exists=native_exists,
        minute_timestamps=minute_rows,
    )


def upsert_evaluation(evaluation: AvailabilityEvaluation) -> None:
    with db_connection(config) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO kline_30m_availability (
                symbol,
                bucket_start,
                target_interval,
                mergeability_status,
                availability_status,
                price_source_type,
                coverage_ratio,
                expected_minutes,
                observed_minutes,
                missing_reason_code,
                session_validity,
                native_30m_exists,
                rule_version,
                evaluated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (symbol, bucket_start, target_interval) DO UPDATE SET
                mergeability_status = EXCLUDED.mergeability_status,
                availability_status = EXCLUDED.availability_status,
                price_source_type = EXCLUDED.price_source_type,
                coverage_ratio = EXCLUDED.coverage_ratio,
                expected_minutes = EXCLUDED.expected_minutes,
                observed_minutes = EXCLUDED.observed_minutes,
                missing_reason_code = EXCLUDED.missing_reason_code,
                session_validity = EXCLUDED.session_validity,
                native_30m_exists = EXCLUDED.native_30m_exists,
                rule_version = EXCLUDED.rule_version,
                evaluated_at = NOW()
            """,
            (
                evaluation.symbol,
                evaluation.bucket_start,
                evaluation.target_interval,
                evaluation.mergeability_status.value,
                evaluation.availability_status.value,
                evaluation.price_source_type.value,
                evaluation.coverage_ratio,
                evaluation.expected_minutes,
                evaluation.observed_minutes,
                evaluation.missing_reason_code,
                evaluation.session_validity,
                evaluation.native_30m_exists,
                evaluation.rule_version,
            ),
        )
        conn.commit()
        cur.close()


def main() -> int:
    parser = argparse.ArgumentParser(description='Audit 30m availability / lineage for sample buckets')
    parser.add_argument('--sample', action='append', default=[], help='Format: symbol@ISO8601 bucket_start')
    parser.add_argument('--write', action='store_true', help='Upsert results into kline_30m_availability')
    args = parser.parse_args()

    samples = [parse_sample(item) for item in args.sample] if args.sample else [
        (symbol, datetime.fromisoformat(ts)) for symbol, ts in DEFAULT_SAMPLES
    ]

    results = []
    for symbol, bucket_start in samples:
        evaluation = evaluate_sample(symbol, bucket_start)
        if args.write:
            upsert_evaluation(evaluation)
        results.append({
            'symbol': evaluation.symbol,
            'bucket_start': evaluation.bucket_start.isoformat(),
            'mergeability_status': evaluation.mergeability_status.value,
            'availability_status': evaluation.availability_status.value,
            'price_source_type': evaluation.price_source_type.value,
            'coverage_ratio': evaluation.coverage_ratio,
            'expected_minutes': evaluation.expected_minutes,
            'observed_minutes': evaluation.observed_minutes,
            'missing_reason_code': evaluation.missing_reason_code,
            'session_validity': evaluation.session_validity,
            'native_30m_exists': evaluation.native_30m_exists,
            'rule_version': RULE_VERSION,
        })

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
