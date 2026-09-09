import pytest

from src.bitmap import CoverageBitmap
from src.coverage_tracker import CoverageTracker


# ============================================================
# BITMAP TESTS
# ============================================================


def test_bitmap_has_default_size():

    bitmap = CoverageBitmap()

    assert len(bitmap) == 65536
    assert bitmap.hit_count() == 0


def test_record_new_edge():

    bitmap = CoverageBitmap()

    assert bitmap.record(1234) is True
    assert bitmap.has_edge(1234)
    assert bitmap.hit_count() == 1


def test_record_existing_edge():

    bitmap = CoverageBitmap()

    bitmap.record(1234)

    assert bitmap.record(1234) is False
    assert bitmap.hit_count() == 1


def test_edge_ids_are_mapped_into_bitmap():

    bitmap = CoverageBitmap(size=16)

    assert bitmap.index(17) == 1
    assert bitmap.index(33) == 1


def test_reset_clears_bitmap():

    bitmap = CoverageBitmap()

    bitmap.record(100)
    bitmap.record(200)

    bitmap.reset()

    assert bitmap.hit_count() == 0
    assert not bitmap.has_edge(100)
    assert not bitmap.has_edge(200)


def test_merge_discovers_new_coverage():

    first = CoverageBitmap()
    second = CoverageBitmap()

    first.record(100)
    second.record(200)

    assert first.merge(second) is True

    assert first.has_edge(100)
    assert first.has_edge(200)
    assert first.hit_count() == 2


def test_merge_without_new_coverage():

    first = CoverageBitmap()
    second = CoverageBitmap()

    first.record(100)
    second.record(100)

    assert first.merge(second) is False


def test_merge_requires_same_size():

    first = CoverageBitmap(size=16)
    second = CoverageBitmap(size=32)

    with pytest.raises(ValueError):
        first.merge(second)


def test_copy_is_independent():

    bitmap = CoverageBitmap()

    bitmap.record(100)

    copied = bitmap.copy()

    copied.record(200)

    assert bitmap.has_edge(100)
    assert not bitmap.has_edge(200)

    assert copied.has_edge(100)
    assert copied.has_edge(200)


def test_invalid_size():

    with pytest.raises(ValueError):
        CoverageBitmap(0)


# ============================================================
# EDGE TRACKER TESTS
# ============================================================


def test_tracker_records_edges():

    tracker = CoverageTracker()
    tracker.enabled = True

    class FakeCode:
        co_filename = "target.py"

    class FakeFrame:
        f_code = FakeCode()
        f_lineno = 10

    tracker.trace(FakeFrame(), "line", None)

    FakeFrame.f_lineno = 20
    tracker.trace(FakeFrame(), "line", None)

    assert tracker.edge_count() == 1
    assert tracker.has_edge(
        (10 << 32) ^ 20
    )


def test_tracker_records_multiple_edges():

    tracker = CoverageTracker()
    tracker.enabled = True

    class FakeCode:
        co_filename = "target.py"

    class FakeFrame:
        f_code = FakeCode()
        f_lineno = 10

    tracker.trace(FakeFrame(), "line", None)

    FakeFrame.f_lineno = 20
    tracker.trace(FakeFrame(), "line", None)

    FakeFrame.f_lineno = 30
    tracker.trace(FakeFrame(), "line", None)

    assert tracker.edge_count() == 2


def test_tracker_ignores_non_target_files():

    tracker = CoverageTracker()
    tracker.enabled = True

    class FakeCode:
        co_filename = "other.py"

    class FakeFrame:
        f_code = FakeCode()
        f_lineno = 10

    tracker.trace(FakeFrame(), "line", None)

    assert tracker.edge_count() == 0
    assert tracker.coverage_count() == 0