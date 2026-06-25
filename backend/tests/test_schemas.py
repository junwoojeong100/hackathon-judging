from datetime import datetime, timedelta, timezone

from app.schemas import SubmissionOut


def _sub(created_at):
    return SubmissionOut(
        id=1,
        team_name="t",
        project_name="p",
        source_type="github",
        source_ref="x",
        stage="interim",
        status="scored",
        error_message="",
        created_at=created_at,
    )


def test_naive_datetime_serialized_as_utc_with_z():
    # SQLite returns naive datetimes whose value is UTC. A naive ISO string would
    # be read as local time by the browser, so it must be emitted with a 'Z'.
    out = _sub(datetime(2026, 6, 25, 0, 19, 50)).model_dump()["created_at"]
    assert out == "2026-06-25T00:19:50Z"


def test_aware_datetime_converted_to_utc():
    kst = timezone(timedelta(hours=9))
    out = _sub(datetime(2026, 6, 25, 9, 19, 50, tzinfo=kst)).model_dump()["created_at"]
    assert out == "2026-06-25T00:19:50Z"  # 09:19 KST == 00:19 UTC
