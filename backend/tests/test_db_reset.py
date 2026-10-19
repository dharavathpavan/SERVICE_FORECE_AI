"""``app.db.reset`` is what keeps a test environment free of demo data.

It deletes rows from every business table, so it is tested like the destructive
operation it is: on the in-memory database, plus the object-storage purge against
a temporary directory. ``reset_database()`` itself is not called here - it binds
to the real engine from ``app.core.database`` and would wipe the developer's
database mid-test.
"""

from pathlib import Path

import pytest

from app.core.config import settings
from app.db.reset import clear_business_data, count_rows, purge_object_storage
from app.models.tenant import Organization, OrganizationMembership, User


def _register(client, email: str = "owner@example.com"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Test Owner",
            "password": "SecretPassword123!",
            "organization_name": "Clean Slate Clinic",
        },
    )


def test_reset_removes_every_business_row(client, db_session):
    assert _register(client).status_code == 201

    before = count_rows(db_session)
    assert before["organizations"] == 1
    assert before["users"] == 1
    assert before["organization_memberships"] == 1

    removed = clear_business_data(db_session)

    assert removed["organizations"] == 1
    assert removed["users"] == 1
    assert sum(count_rows(db_session).values()) == 0
    assert db_session.query(Organization).count() == 0
    assert db_session.query(User).count() == 0
    assert db_session.query(OrganizationMembership).count() == 0


def test_reset_leaves_the_schema_usable(client, db_session):
    assert _register(client).status_code == 201
    clear_business_data(db_session)

    # The tables still exist and still accept writes.
    assert _register(client, email="second@example.com").status_code == 201
    assert db_session.query(Organization).count() == 1


def test_reset_is_idempotent(client, db_session):
    assert sum(clear_business_data(db_session).values()) == 0
    assert sum(clear_business_data(db_session).values()) == 0
    assert sum(count_rows(db_session).values()) == 0


def test_reset_reports_nothing_removed_for_an_empty_database(db_session):
    assert sum(count_rows(db_session).values()) == 0


def test_object_storage_purge_removes_recordings_and_documents(tmp_path: Path):
    nested = tmp_path / "recordings" / "2026"
    nested.mkdir(parents=True)
    (nested / "call.wav").write_bytes(b"RIFF....WAVE")
    (tmp_path / "document.pdf").write_bytes(b"%PDF-1.4")

    files, size = purge_object_storage(tmp_path)

    assert files == 2
    assert size == len(b"RIFF....WAVE") + len(b"%PDF-1.4")
    assert not any(path.is_file() for path in tmp_path.rglob("*"))
    assert tmp_path.is_dir()


def test_storage_root_refuses_a_repository_root(tmp_path: Path, monkeypatch):
    (tmp_path / "app").mkdir()
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "STORAGE_LOCAL_PATH", str(tmp_path))

    from app.db.reset import _storage_root

    with pytest.raises(RuntimeError, match="refusing to purge"):
        _storage_root()


def test_storage_root_is_none_when_the_directory_does_not_exist(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "STORAGE_LOCAL_PATH", str(tmp_path / "missing"))

    from app.db.reset import _storage_root

    assert _storage_root() is None
