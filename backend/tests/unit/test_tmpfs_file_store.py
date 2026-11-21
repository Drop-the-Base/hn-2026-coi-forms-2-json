import os
import stat
import time
import uuid
from pathlib import Path

import pytest

from forms2json.adapters.outbound.storage.tmpfs_file_store import TmpfsFileStore

TTL_SECONDS = 60


@pytest.fixture
def store(tmp_path: Path) -> TmpfsFileStore:
    return TmpfsFileStore(tmp_path / "jobs", ttl_seconds=TTL_SECONDS)


def test_saved_file_is_readable_owner_only_and_gone_after_delete(
    store: TmpfsFileStore, tmp_path: Path
) -> None:
    job_id = str(uuid.uuid4())

    store.save(job_id, b"form")

    assert store.read(job_id) == b"form"
    assert stat.S_IMODE((tmp_path / "jobs" / job_id).stat().st_mode) == 0o600
    store.delete(job_id)
    with pytest.raises(FileNotFoundError):
        store.read(job_id)
    store.delete(job_id)  # idempotent


def test_save_does_not_overwrite_an_existing_job_file(store: TmpfsFileStore) -> None:
    job_id = str(uuid.uuid4())
    store.save(job_id, b"first")

    with pytest.raises(FileExistsError):
        store.save(job_id, b"second")
    assert store.read(job_id) == b"first"


def test_delete_expired_removes_old_files_and_keeps_fresh_ones(
    store: TmpfsFileStore, tmp_path: Path
) -> None:
    old_job, fresh_job = str(uuid.uuid4()), str(uuid.uuid4())
    store.save(old_job, b"old")
    store.save(fresh_job, b"fresh")
    past = time.time() - TTL_SECONDS - 1
    os.utime(tmp_path / "jobs" / old_job, (past, past))

    store.delete_expired()

    with pytest.raises(FileNotFoundError):
        store.read(old_job)
    assert store.read(fresh_job) == b"fresh"


@pytest.mark.parametrize("job_id", ["../escape", "/etc/passwd", "..", "", "abc"])
def test_non_uuid_job_id_is_rejected(store: TmpfsFileStore, tmp_path: Path, job_id: str) -> None:
    with pytest.raises(ValueError):
        store.save(job_id, b"x")
    with pytest.raises(ValueError):
        store.read(job_id)
    with pytest.raises(ValueError):
        store.delete(job_id)
    assert not (tmp_path / "escape").exists()
