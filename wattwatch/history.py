"""SQLite reads for the local history endpoints: downsampling and summary.

Bucketing is done in SQL (`ts / bucket_size` integer division with `GROUP BY`
and `AVG`) so long ranges stay cheap — we never pull every row into Python.
`ts` is stored as unix epoch seconds (UTC); conversion to ISO-8601 with
timezone happens only at the API boundary (in the router).
"""

import sqlite3
from dataclasses import dataclass
from itertools import pairwise

from wattwatch import db

MAX_HISTORY_POINTS = 720


@dataclass(slots=True)
class HistoryPoint:
    ts: int
    power_w: float | None
    voltage_v: float | None
    current_a: float | None


@dataclass(slots=True)
class HistorySummary:
    count: int
    avg_power_w: float | None
    min_power_w: float | None
    max_power_w: float | None
    energy_kwh: float | None


def _query_points(
    conn: sqlite3.Connection, start_ts: int, end_ts: int, bucket_size: int
) -> list[HistoryPoint]:
    if bucket_size <= 1:
        rows = conn.execute(
            "SELECT ts, power_w, voltage_v, current_a FROM readings "
            "WHERE ts >= ? AND ts <= ? ORDER BY ts ASC",
            (start_ts, end_ts),
        ).fetchall()
        return [HistoryPoint(ts=r[0], power_w=r[1], voltage_v=r[2], current_a=r[3]) for r in rows]

    rows = conn.execute(
        "SELECT (ts / ?) * ? AS bucket, AVG(power_w), AVG(voltage_v), AVG(current_a) "
        "FROM readings WHERE ts >= ? AND ts <= ? "
        "GROUP BY bucket ORDER BY bucket ASC",
        (bucket_size, bucket_size, start_ts, end_ts),
    ).fetchall()
    return [HistoryPoint(ts=r[0], power_w=r[1], voltage_v=r[2], current_a=r[3]) for r in rows]


async def get_history(start_ts: int, end_ts: int) -> list[HistoryPoint]:
    """Return at most `MAX_HISTORY_POINTS` bucket-averaged points, ascending by ts."""
    span = max(1, end_ts - start_ts)
    # Buckets are aligned to absolute epoch boundaries, not to start_ts, so a
    # span covers up to span/bucket_size + 1 of them. Dividing by one fewer
    # than the cap keeps that "+ 1" inside MAX_HISTORY_POINTS.
    bucket_size = max(1, -(-span // (MAX_HISTORY_POINTS - 1)))  # ceil division
    return await db.run(_query_points, start_ts, end_ts, bucket_size)


def _query_summary(conn: sqlite3.Connection, start_ts: int, end_ts: int) -> HistorySummary:
    row = conn.execute(
        "SELECT COUNT(*), AVG(power_w), MIN(power_w), MAX(power_w) FROM readings "
        "WHERE ts >= ? AND ts <= ?",
        (start_ts, end_ts),
    ).fetchone()
    count, avg_power, min_power, max_power = row
    count = count or 0

    energy_kwh: float | None = None
    if count > 0:
        ordered = conn.execute(
            "SELECT ts, power_w FROM readings WHERE ts >= ? AND ts <= ? ORDER BY ts ASC",
            (start_ts, end_ts),
        ).fetchall()
        energy_kwh = _integrate_energy_kwh(ordered)

    return HistorySummary(
        count=count,
        avg_power_w=avg_power,
        min_power_w=min_power,
        max_power_w=max_power,
        energy_kwh=energy_kwh,
    )


def _integrate_energy_kwh(rows: list[tuple[int, float | None]]) -> float | None:
    """Trapezoidal integration of power (W) over time (s) -> energy (kWh)."""
    samples = [(ts, power) for ts, power in rows if power is not None]
    if not samples:
        return None
    if len(samples) == 1:
        return 0.0
    joules = 0.0
    for (ts_a, p_a), (ts_b, p_b) in pairwise(samples):
        dt = ts_b - ts_a
        if dt <= 0:
            continue
        joules += (p_a + p_b) / 2 * dt
    return joules / 3_600_000


async def get_summary(start_ts: int, end_ts: int) -> HistorySummary:
    return await db.run(_query_summary, start_ts, end_ts)
