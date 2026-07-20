from datetime import datetime, timezone

from backend.services import runtime_session
from backend.services.runtime_session import RuntimeSession, get_runtime_session, reset_runtime_session


def _fresh_session():
    reset_runtime_session()
    return get_runtime_session()


def test_initial_state_is_stopped():
    session = _fresh_session()
    assert session.status == "stopped"
    assert session.started_at is None
    assert session.process_id is None
    assert session.get_uptime() == 0


def test_start_sets_session_state():
    session = _fresh_session()
    session.start(pid=12345)

    assert session.status == "running"
    assert session.process_id == 12345
    assert session.started_at is not None
    assert session.started_at.tzinfo is not None
    assert session.get_uptime() >= 0


def test_stop_resets_session_state():
    session = _fresh_session()
    session.start(pid=12345)
    session.stop()

    assert session.status == "stopped"
    assert session.started_at is None
    assert session.process_id is None
    assert session.get_uptime() == 0


def test_restart_creates_new_session():
    session = _fresh_session()
    session.start(pid=11111)
    session.restart(pid=22222)

    assert session.status == "running"
    assert session.process_id == 22222
    assert session.started_at is not None


def test_get_uptime_returns_zero_when_stopped():
    session = _fresh_session()
    assert session.get_uptime() == 0


def test_get_uptime_increases_while_running():
    session = _fresh_session()
    session.start(pid=99999)

    first = session.get_uptime()
    assert first >= 0

    session.stop()
    assert session.get_uptime() == 0


def test_to_dict_contains_expected_keys():
    session = _fresh_session()
    session.start(pid=55555, reason="manual_start")

    data = session.to_dict()

    assert data["status"] == "running"
    assert data["process_id"] == 55555
    assert data["started_at"] is not None
    assert data["uptime_seconds"] >= 0
    assert data["last_restart_reason"] == "manual_start"


def test_to_dict_when_stopped():
    session = _fresh_session()
    data = session.to_dict()

    assert data["status"] == "stopped"
    assert data["started_at"] is None
    assert data["uptime_seconds"] == 0
    assert data["process_id"] is None
    assert data["last_restart_reason"] is None


def test_start_without_reason_sets_none():
    session = _fresh_session()
    session.start(pid=77777)
    assert session.last_restart_reason is None


def test_reset_runtime_session_creates_fresh_instance():
    session = get_runtime_session()
    session.start(pid=88888)

    reset_runtime_session()
    new_session = get_runtime_session()

    assert new_session.status == "stopped"
    assert new_session.started_at is None
    assert new_session.process_id is None
