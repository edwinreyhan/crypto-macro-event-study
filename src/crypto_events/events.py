"""Macro events (CPI releases, FOMC and BI rate decisions) from ``seeds/events.csv``.

Each row stores the official **local** announcement time plus its IANA time zone, and the
same moment in UTC. The UTC column must always equal the converted local time; never
hard-code UTC offsets (New York changes between UTC-5 and UTC-4 during the year).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "seeds" / "events.csv"

COLUMNS = [
    "event_id",
    "type",
    "country",
    "announced_at_local",
    "tz",
    "announced_at_utc",
    "time_precision",
    "decision",
    "source_url",
    "notes",
]
TYPES = {"CPI", "FOMC", "BI"}
PRECISIONS = {"minute", "approx_30min"}
RATE_DECISIONS = {"hike", "hold", "cut"}


@dataclass(frozen=True)
class Event:
    event_id: str
    type: str
    country: str
    announced_at_local: datetime  # naive, in ``tz``
    tz: str
    announced_at_utc: datetime  # timezone-aware, UTC
    time_precision: str
    decision: str
    source_url: str
    notes: str


def local_to_utc(local: datetime, tz: str) -> datetime:
    """Interpret a naive local time in ``tz`` and return it as an aware UTC datetime."""
    return local.replace(tzinfo=ZoneInfo(tz)).astimezone(UTC)


def parse_row(row: dict[str, str]) -> Event:
    """Turn one CSV row into an Event, raising ValueError if anything is wrong."""
    event_id = row["event_id"]
    if row["type"] not in TYPES:
        raise ValueError(f"{event_id}: unknown type {row['type']!r}")
    if row["time_precision"] not in PRECISIONS:
        raise ValueError(f"{event_id}: unknown time_precision {row['time_precision']!r}")
    if not row["source_url"].startswith("https://"):
        raise ValueError(f"{event_id}: source_url must be an https link")

    is_rate_decision = row["type"] in {"FOMC", "BI"}
    if is_rate_decision and row["decision"] not in RATE_DECISIONS:
        raise ValueError(f"{event_id}: decision must be one of {sorted(RATE_DECISIONS)}")
    if not is_rate_decision and row["decision"]:
        raise ValueError(f"{event_id}: only rate decisions have a decision")

    local = datetime.fromisoformat(row["announced_at_local"])
    utc = datetime.fromisoformat(row["announced_at_utc"].replace("Z", "+00:00"))
    if local.tzinfo is not None:
        raise ValueError(f"{event_id}: announced_at_local must not include an offset")
    if utc != local_to_utc(local, row["tz"]):
        raise ValueError(f"{event_id}: announced_at_utc does not match local time in {row['tz']}")

    return Event(
        event_id=event_id,
        type=row["type"],
        country=row["country"],
        announced_at_local=local,
        tz=row["tz"],
        announced_at_utc=utc,
        time_precision=row["time_precision"],
        decision=row["decision"],
        source_url=row["source_url"],
        notes=row["notes"],
    )


def load_events(path: Path = DEFAULT_PATH) -> list[Event]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"{path}: columns must be {COLUMNS}, got {reader.fieldnames}")
        events = [parse_row(row) for row in reader]
    ids = [e.event_id for e in events]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate event_id")
    return events
