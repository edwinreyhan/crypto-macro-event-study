from collections import Counter
from datetime import UTC, datetime

import pytest

from crypto_events.events import COLUMNS, load_events, parse_row


@pytest.fixture(scope="module")
def events():
    return load_events()


def test_every_row_is_valid(events):
    # load_events() raises on any bad row, so getting here means every row passed.
    assert len(events) == 39


def test_counts_per_type_and_year(events):
    counts = Counter((e.type, e.announced_at_utc.year) for e in events)
    assert counts[("FOMC", 2024)] == 8
    assert counts[("FOMC", 2025)] == 8
    assert counts[("CPI", 2024)] == 12
    assert counts[("CPI", 2025)] == 11  # October 2025 CPI was cancelled


@pytest.mark.parametrize(
    "event_id, expected_utc",
    [
        ("cpi-2024-01-11", datetime(2024, 1, 11, 13, 30, tzinfo=UTC)),  # winter, EST
        ("cpi-2024-03-12", datetime(2024, 3, 12, 12, 30, tzinfo=UTC)),  # 2 days after DST start
        ("fomc-2025-01-29", datetime(2025, 1, 29, 19, 0, tzinfo=UTC)),  # winter, EST
        ("fomc-2025-09-17", datetime(2025, 9, 17, 18, 0, tzinfo=UTC)),  # summer, EDT
        ("fomc-2025-10-29", datetime(2025, 10, 29, 18, 0, tzinfo=UTC)),  # before DST ends (Nov 2)
    ],
)
def test_daylight_saving_is_applied(events, event_id, expected_utc):
    by_id = {e.event_id: e for e in events}
    assert by_id[event_id].announced_at_utc == expected_utc


def test_rescheduled_cpi_uses_actual_date(events):
    ids = {e.event_id for e in events}
    assert "cpi-2025-10-24" in ids  # September CPI, moved from 2025-10-15
    assert "cpi-2025-10-15" not in ids
    assert "cpi-2025-12-18" in ids  # November CPI, moved from 2025-12-10


def test_events_are_sorted_by_time(events):
    times = [e.announced_at_utc for e in events]
    assert times == sorted(times)


def good_row(**overrides):
    row = {
        "event_id": "fomc-2025-01-29",
        "type": "FOMC",
        "country": "US",
        "announced_at_local": "2025-01-29T14:00:00",
        "tz": "America/New_York",
        "announced_at_utc": "2025-01-29T19:00:00Z",
        "time_precision": "minute",
        "decision": "hold",
        "source_url": "https://www.federalreserve.gov/x.htm",
        "notes": "",
    }
    assert list(row) == COLUMNS
    return {**row, **overrides}


@pytest.mark.parametrize(
    "overrides",
    [
        {"announced_at_utc": "2025-01-29T18:00:00Z"},  # wrong offset (used EDT in January)
        {"type": "ECB"},
        {"decision": "pause"},
        {"time_precision": "hour"},
        {"source_url": "http://insecure.example"},
        {"type": "CPI", "decision": "hold"},  # CPI has no decision
        {"announced_at_local": "2025-01-29T14:00:00-05:00"},  # local must be naive
    ],
)
def test_bad_rows_are_rejected(overrides):
    with pytest.raises(ValueError):
        parse_row(good_row(**overrides))


def test_good_row_is_accepted():
    assert parse_row(good_row()).announced_at_utc == datetime(2025, 1, 29, 19, 0, tzinfo=UTC)
