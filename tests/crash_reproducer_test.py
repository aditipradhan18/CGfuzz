from src.crash_reproducer import (
    CrashReproducer,
    ReproductionResult,
)
from src.executor import (
    Executor,
    ExecutionStatus,
)


def crashing_target(data: bytes):
    if data == b"CRASH":
        raise RuntimeError("intentional crash")

    return "OK"


def normal_target(data: bytes):
    return "OK"


def timeout_target(data: bytes):
    raise TimeoutError("intentional timeout")


def test_reproducer_detects_crash():

    executor = Executor(
        crashing_target
    )

    reproducer = CrashReproducer(
        executor,
        attempts=3
    )

    result = reproducer.reproduce(
        b"CRASH"
    )

    assert isinstance(
        result,
        ReproductionResult
    )

    assert result.reproduced is True
    assert result.attempts == 3
    assert result.crashes == 3
    assert result.normal == 0
    assert result.timeouts == 0


def test_reproducer_detects_normal_input():

    executor = Executor(
        normal_target
    )

    reproducer = CrashReproducer(
        executor,
        attempts=3
    )

    result = reproducer.reproduce(
        b"HELLO"
    )

    assert result.reproduced is False
    assert result.attempts == 3
    assert result.crashes == 0
    assert result.normal == 3
    assert result.timeouts == 0


def test_reproducer_detects_timeout():

    executor = Executor(
        timeout_target
    )

    reproducer = CrashReproducer(
        executor,
        attempts=3
    )

    result = reproducer.reproduce(
        b"TIMEOUT"
    )

    assert result.reproduced is False
    assert result.attempts == 3
    assert result.crashes == 0
    assert result.normal == 0
    assert result.timeouts == 3


def test_is_reproducible():

    executor = Executor(
        crashing_target
    )

    reproducer = CrashReproducer(
        executor,
        attempts=3
    )

    assert reproducer.is_reproducible(
        b"CRASH"
    ) is True


def test_is_not_reproducible():

    executor = Executor(
        normal_target
    )

    reproducer = CrashReproducer(
        executor,
        attempts=3
    )

    assert reproducer.is_reproducible(
        b"HELLO"
    ) is False


def test_single_verification():

    executor = Executor(
        crashing_target
    )

    reproducer = CrashReproducer(
        executor
    )

    assert reproducer.verify(
        b"CRASH"
    ) is True

    assert reproducer.verify(
        b"HELLO"
    ) is False


def test_invalid_attempt_count():

    executor = Executor(
        crashing_target
    )

    try:
        CrashReproducer(
            executor,
            attempts=0
        )

        assert False

    except ValueError:
        assert True