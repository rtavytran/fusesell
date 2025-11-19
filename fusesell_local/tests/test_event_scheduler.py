from datetime import datetime

from fusesell_local.utils.event_scheduler import EventScheduler


def test_format_datetime_rounds_to_minute(tmp_path):
    scheduler = EventScheduler(data_dir=str(tmp_path))

    dt = datetime(2025, 1, 1, 12, 34, 56, 987654)
    rounded_iso = scheduler._format_datetime(dt)
    parsed = datetime.fromisoformat(rounded_iso)
    assert parsed.second == 0
    assert parsed.microsecond == 0


def test_format_datetime_rounds_string_values(tmp_path):
    scheduler = EventScheduler(data_dir=str(tmp_path))

    rounded_iso = scheduler._format_datetime("2025-01-01T23:59:45.123456")
    parsed = datetime.fromisoformat(rounded_iso)
    assert parsed.second == 0
    assert parsed.microsecond == 0
