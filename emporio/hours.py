from datetime import datetime, time, timedelta, timezone

STORE_TZ = timezone(timedelta(hours=-4))
# 2026 national holidays, official MGI calendar. Local/special closures still require confirmation.
NATIONAL_HOLIDAYS_2026 = {"2026-01-01", "2026-04-03", "2026-04-21", "2026-05-01", "2026-09-07",
                          "2026-10-12", "2026-11-02", "2026-11-15", "2026-11-20", "2026-12-25"}


def human_service(at: datetime | None = None) -> dict:
    current = (at or datetime.now(STORE_TZ)).astimezone(STORE_TZ)

    def schedule(day):
        if day.weekday() == 6 or day.isoformat() in NATIONAL_HOLIDAYS_2026:
            return None
        return time(9), time(13) if day.weekday() == 5 else time(18)

    hours = schedule(current.date())
    opened = bool(hours and hours[0] <= current.time().replace(tzinfo=None) < hours[1])
    next_opening = None
    if not opened:
        for offset in range(8):
            candidate = current.date() + timedelta(days=offset)
            candidate_hours = schedule(candidate)
            if candidate_hours:
                start = datetime.combine(candidate, candidate_hours[0], STORE_TZ)
                if start > current:
                    next_opening = start.isoformat()
                    break
    return {"open_now": opened, "next_scheduled_opening": next_opening,
            "timezone": "Campo Grande (UTC-04:00)",
            "notice": "Regular schedule and 2026 national holidays only; special or local closures require team confirmation."}
