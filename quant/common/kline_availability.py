"""
30m availability / lineage minimal helper.

本模块只负责：
- 冻结最小状态枚举
- 提供 1m -> 30m 严格可合并判定
- 提供最小 availability / lineage 表初始化 SQL

刻意不做：
- 不写入/污染 kline_data
- 不做 verification 全量改造
- 不做宽松覆盖率阈值
- 不做完整交易日历系统
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Iterable, Sequence


RULE_VERSION = 'availability_lineage_v1'
TARGET_INTERVAL = '30m'
SOURCE_INTERVAL = '1m'
EXPECTED_MINUTES_30M_STRICT = 30


class MergeabilityStatus(StrEnum):
    """Frozen minimal mergeability statuses for 30m buckets."""

    NATIVE_30M = 'NATIVE_30M'
    MERGEABLE_FROM_1M = 'MERGEABLE_FROM_1M'
    NOT_MERGEABLE_1M_GAP = 'NOT_MERGEABLE_1M_GAP'
    NOT_MERGEABLE_NO_1M = 'NOT_MERGEABLE_NO_1M'
    NOT_MERGEABLE_CROSS_SESSION = 'NOT_MERGEABLE_CROSS_SESSION'
    UNKNOWN_CALENDAR = 'UNKNOWN_CALENDAR'


class AvailabilityStatus(StrEnum):
    AVAILABLE_NATIVE = 'AVAILABLE_NATIVE'
    AVAILABLE_AGGREGATED = 'AVAILABLE_AGGREGATED'
    UNAVAILABLE_NOT_MERGEABLE = 'UNAVAILABLE_NOT_MERGEABLE'
    UNAVAILABLE_UNKNOWN = 'UNAVAILABLE_UNKNOWN'


class PriceSourceType(StrEnum):
    NATIVE_30M = 'NATIVE_30M'
    AGGREGATED_FROM_1M = 'AGGREGATED_FROM_1M'
    NONE = 'NONE'


class MissingReasonCode(StrEnum):
    NO_NATIVE_30M = 'NO_NATIVE_30M'
    NO_1M_DATA = 'NO_1M_DATA'
    PARTIAL_1M_COVERAGE = 'PARTIAL_1M_COVERAGE'
    CROSS_SESSION_BUCKET = 'CROSS_SESSION_BUCKET'
    UNKNOWN_TRADING_CALENDAR = 'UNKNOWN_TRADING_CALENDAR'


@dataclass(frozen=True)
class AvailabilityEvaluation:
    symbol: str
    bucket_start: datetime
    target_interval: str
    mergeability_status: MergeabilityStatus
    availability_status: AvailabilityStatus
    price_source_type: PriceSourceType
    coverage_ratio: float
    expected_minutes: int
    observed_minutes: int
    missing_reason_code: str | None
    session_validity: str
    native_30m_exists: bool
    rule_version: str = RULE_VERSION


DAY_SESSIONS = (
    ((9, 0), (10, 15)),
    ((10, 30), (11, 30)),
    ((13, 30), (15, 0)),
)
NIGHT_SESSIONS = (
    ((21, 0), (23, 59)),
    ((0, 0), (2, 30)),
)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS kline_30m_availability (
    symbol VARCHAR(20) NOT NULL,
    bucket_start TIMESTAMPTZ NOT NULL,
    target_interval VARCHAR(10) NOT NULL,
    mergeability_status VARCHAR(64) NOT NULL,
    availability_status VARCHAR(64) NOT NULL,
    price_source_type VARCHAR(64) NOT NULL,
    coverage_ratio DECIMAL(8, 6),
    expected_minutes INTEGER NOT NULL,
    observed_minutes INTEGER NOT NULL,
    missing_reason_code VARCHAR(64),
    session_validity VARCHAR(32) NOT NULL,
    native_30m_exists BOOLEAN NOT NULL DEFAULT FALSE,
    rule_version VARCHAR(64) NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, bucket_start, target_interval)
)
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_kline_30m_availability_status
ON kline_30m_availability (symbol, mergeability_status, bucket_start DESC)
"""


def floor_to_30m_bucket(value: datetime) -> datetime:
    minute = (value.minute // 30) * 30
    return value.replace(minute=minute, second=0, microsecond=0)


def _minute_in_windows(dt: datetime, windows: Sequence[tuple[tuple[int, int], tuple[int, int]]]) -> bool:
    current = dt.hour * 60 + dt.minute
    for start, end in windows:
        start_minute = start[0] * 60 + start[1]
        end_minute = end[0] * 60 + end[1]
        if start_minute <= current <= end_minute:
            return True
    return False


def classify_session(dt: datetime) -> str:
    if _minute_in_windows(dt, DAY_SESSIONS):
        return 'DAY'
    if _minute_in_windows(dt, NIGHT_SESSIONS):
        return 'NIGHT'
    return 'CLOSED'


def expected_bucket_minutes(bucket_start: datetime) -> list[datetime] | None:
    minutes = [bucket_start + timedelta(minutes=i) for i in range(EXPECTED_MINUTES_30M_STRICT)]
    sessions = {classify_session(ts) for ts in minutes}
    if 'CLOSED' in sessions:
        return None
    if len(sessions) != 1:
        return None
    return minutes


def normalize_minute_timestamps(values: Iterable[datetime]) -> list[datetime]:
    normalized = {
        value.replace(second=0, microsecond=0)
        for value in values
    }
    return sorted(normalized)


def evaluate_bucket(
    *,
    symbol: str,
    bucket_start: datetime,
    native_30m_exists: bool,
    minute_timestamps: Iterable[datetime],
) -> AvailabilityEvaluation:
    if native_30m_exists:
        return AvailabilityEvaluation(
            symbol=symbol,
            bucket_start=bucket_start,
            target_interval=TARGET_INTERVAL,
            mergeability_status=MergeabilityStatus.NATIVE_30M,
            availability_status=AvailabilityStatus.AVAILABLE_NATIVE,
            price_source_type=PriceSourceType.NATIVE_30M,
            coverage_ratio=1.0,
            expected_minutes=EXPECTED_MINUTES_30M_STRICT,
            observed_minutes=EXPECTED_MINUTES_30M_STRICT,
            missing_reason_code=None,
            session_validity='NATIVE',
            native_30m_exists=True,
        )

    expected_minutes = expected_bucket_minutes(bucket_start)
    observed = normalize_minute_timestamps(minute_timestamps)

    if expected_minutes is None:
        sessions = {classify_session(bucket_start + timedelta(minutes=i)) for i in range(EXPECTED_MINUTES_30M_STRICT)}
        if 'CLOSED' in sessions:
            return AvailabilityEvaluation(
                symbol=symbol,
                bucket_start=bucket_start,
                target_interval=TARGET_INTERVAL,
                mergeability_status=MergeabilityStatus.NOT_MERGEABLE_CROSS_SESSION,
                availability_status=AvailabilityStatus.UNAVAILABLE_NOT_MERGEABLE,
                price_source_type=PriceSourceType.NONE,
                coverage_ratio=0.0 if not observed else len(observed) / EXPECTED_MINUTES_30M_STRICT,
                expected_minutes=EXPECTED_MINUTES_30M_STRICT,
                observed_minutes=len(observed),
                missing_reason_code=MissingReasonCode.CROSS_SESSION_BUCKET,
                session_validity='CROSS_SESSION',
                native_30m_exists=False,
            )
        return AvailabilityEvaluation(
            symbol=symbol,
            bucket_start=bucket_start,
            target_interval=TARGET_INTERVAL,
            mergeability_status=MergeabilityStatus.UNKNOWN_CALENDAR,
            availability_status=AvailabilityStatus.UNAVAILABLE_UNKNOWN,
            price_source_type=PriceSourceType.NONE,
            coverage_ratio=0.0 if not observed else len(observed) / EXPECTED_MINUTES_30M_STRICT,
            expected_minutes=EXPECTED_MINUTES_30M_STRICT,
            observed_minutes=len(observed),
            missing_reason_code=MissingReasonCode.UNKNOWN_TRADING_CALENDAR,
            session_validity='UNKNOWN_CALENDAR',
            native_30m_exists=False,
        )

    expected_set = set(expected_minutes)
    observed_in_bucket = sorted(ts for ts in observed if ts in expected_set)
    observed_count = len(observed_in_bucket)
    coverage_ratio = observed_count / len(expected_minutes)

    if observed_count == 0:
        return AvailabilityEvaluation(
            symbol=symbol,
            bucket_start=bucket_start,
            target_interval=TARGET_INTERVAL,
            mergeability_status=MergeabilityStatus.NOT_MERGEABLE_NO_1M,
            availability_status=AvailabilityStatus.UNAVAILABLE_NOT_MERGEABLE,
            price_source_type=PriceSourceType.NONE,
            coverage_ratio=0.0,
            expected_minutes=len(expected_minutes),
            observed_minutes=0,
            missing_reason_code=MissingReasonCode.NO_1M_DATA,
            session_validity=classify_session(bucket_start),
            native_30m_exists=False,
        )

    if observed_count == len(expected_minutes):
        return AvailabilityEvaluation(
            symbol=symbol,
            bucket_start=bucket_start,
            target_interval=TARGET_INTERVAL,
            mergeability_status=MergeabilityStatus.MERGEABLE_FROM_1M,
            availability_status=AvailabilityStatus.AVAILABLE_AGGREGATED,
            price_source_type=PriceSourceType.AGGREGATED_FROM_1M,
            coverage_ratio=coverage_ratio,
            expected_minutes=len(expected_minutes),
            observed_minutes=observed_count,
            missing_reason_code=MissingReasonCode.NO_NATIVE_30M,
            session_validity=classify_session(bucket_start),
            native_30m_exists=False,
        )

    return AvailabilityEvaluation(
        symbol=symbol,
        bucket_start=bucket_start,
        target_interval=TARGET_INTERVAL,
        mergeability_status=MergeabilityStatus.NOT_MERGEABLE_1M_GAP,
        availability_status=AvailabilityStatus.UNAVAILABLE_NOT_MERGEABLE,
        price_source_type=PriceSourceType.NONE,
        coverage_ratio=coverage_ratio,
        expected_minutes=len(expected_minutes),
        observed_minutes=observed_count,
        missing_reason_code=MissingReasonCode.PARTIAL_1M_COVERAGE,
        session_validity=classify_session(bucket_start),
        native_30m_exists=False,
    )
