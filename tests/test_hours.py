from datetime import datetime

from emporio.hours import STORE_TZ, human_service


def test_next_opening_skips_sunday_and_finados():
    status = human_service(datetime(2026, 10, 31, 22, 0, tzinfo=STORE_TZ))
    assert not status["open_now"]
    assert status["next_scheduled_opening"] == "2026-11-03T09:00:00-04:00"


def test_closing_time_is_exclusive():
    assert human_service(datetime(2026, 10, 30, 17, 59, tzinfo=STORE_TZ))["open_now"]
    assert not human_service(datetime(2026, 10, 30, 18, 0, tzinfo=STORE_TZ))["open_now"]
