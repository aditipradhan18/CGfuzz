from src.crash_database import CrashDatabase


def test_new_crash_is_added(tmp_path):

    db = CrashDatabase(tmp_path)

    result = db.add_crash(
        "ValueError: invalid input",
        b"AAAA"
    )

    assert result is True
    assert db.count() == 1


def test_duplicate_crash_is_rejected(tmp_path):

    db = CrashDatabase(tmp_path)

    db.add_crash(
        "ValueError: invalid input",
        b"AAAA"
    )

    result = db.add_crash(
        "ValueError: invalid input",
        b"BBBB"
    )

    assert result is False
    assert db.count() == 1


def test_different_crashes_are_stored(tmp_path):

    db = CrashDatabase(tmp_path)

    db.add_crash(
        "ValueError: invalid input",
        b"AAAA"
    )

    db.add_crash(
        "IndexError: out of range",
        b"BBBB"
    )

    assert db.count() == 2


def test_crash_files_are_created(tmp_path):

    db = CrashDatabase(tmp_path)

    db.add_crash(
        "RuntimeError: bad state",
        b"CRASH"
    )

    hashes = db.get_crashes()

    assert len(hashes) == 1

    crash_hash = hashes[0]

    assert (
        tmp_path / f"crash_{crash_hash}.bin"
    ).exists()

    assert (
        tmp_path / f"crash_{crash_hash}.txt"
    ).exists()


def test_hash_is_stable(tmp_path):

    db = CrashDatabase(tmp_path)

    hash1 = db.get_hash("same crash")
    hash2 = db.get_hash("same crash")

    assert hash1 == hash2


def test_database_persists(tmp_path):

    db = CrashDatabase(tmp_path)

    db.add_crash(
        "Segmentation fault",
        b"AAAA"
    )

    db2 = CrashDatabase(tmp_path)

    assert db2.count() == 1
    assert db2.is_duplicate("Segmentation fault")