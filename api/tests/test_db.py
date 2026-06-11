from app import db


def test_check_postgres_runs_select_1(monkeypatch) -> None:
    executed: list[str] = []

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *exc) -> None:
            return None

        def execute(self, stmt) -> None:
            executed.append(str(stmt))

    class FakeEngine:
        def connect(self) -> FakeConn:
            return FakeConn()

    monkeypatch.setattr(db, "get_engine", lambda: FakeEngine())

    assert db.check_postgres() is True
    assert executed == ["SELECT 1"]


def test_check_postgres_propagates_failure(monkeypatch) -> None:
    class DeadEngine:
        def connect(self):
            raise OSError("connection refused")

    monkeypatch.setattr(db, "get_engine", lambda: DeadEngine())

    # The health probe wraps this in try/except; check_postgres itself raises.
    try:
        db.check_postgres()
    except OSError:
        pass
    else:
        raise AssertionError("expected check_postgres to raise when DB is down")
