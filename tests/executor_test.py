from pathlib import Path

from src.executor import (
    Executor,
    ExecutionStatus
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


TARGET = (
    PROJECT_ROOT
    / "src"
    / "target.py"
)


NATIVE_TARGET = (
    PROJECT_ROOT
    / "native_targets"
    / "vulnerable.exe"
)


def test_normal_execution():

    executor = Executor(str(TARGET))
    result = executor.run(b"HELLO")

    assert result.status == ExecutionStatus.NORMAL
    assert result.exit_code == 0
    assert result.duration >= 0


def test_crash_execution():

    executor = Executor(str(TARGET))
    result = executor.run(b"CRASH")

    assert result.status == ExecutionStatus.CRASH
    assert result.exit_code != 0
    assert result.duration >= 0


def test_empty_input():

    executor = Executor(str(TARGET))
    result = executor.run(b"")

    assert result.status in (
        ExecutionStatus.NORMAL,
        ExecutionStatus.CRASH
    )

    assert result.duration >= 0


def test_coverage_is_parsed():

    executor = Executor(str(TARGET))
    result = executor.run(b"HELLO")

    assert isinstance(result.coverage, set)


def test_stdout_is_bytes():

    executor = Executor(str(TARGET))
    result = executor.run(b"HELLO")

    assert isinstance(result.stdout, bytes)


def test_stderr_is_bytes():

    executor = Executor(str(TARGET))
    result = executor.run(b"HELLO")

    assert isinstance(result.stderr, bytes)


# =========================================================
# NATIVE TARGET TESTS
# =========================================================


def test_native_normal_execution():

    executor = Executor(str(NATIVE_TARGET))
    result = executor.run(b"NORMAL")

    assert result.status == ExecutionStatus.NORMAL
    assert result.exit_code == 0
    assert result.duration >= 0


def test_native_crash_execution():

    executor = Executor(str(NATIVE_TARGET))
    result = executor.run(b"CRASH")

    assert result.status == ExecutionStatus.CRASH
    assert result.exit_code != 0
    assert result.duration >= 0


def test_native_stdout_is_bytes():

    executor = Executor(str(NATIVE_TARGET))
    result = executor.run(b"FUZZ")

    assert isinstance(result.stdout, bytes)


def test_native_stderr_is_bytes():

    executor = Executor(str(NATIVE_TARGET))
    result = executor.run(b"FUZZ")

    assert isinstance(result.stderr, bytes)


def test_native_coverage_is_empty_until_instrumented():

    executor = Executor(str(NATIVE_TARGET))
    result = executor.run(b"FUZZ")

    assert isinstance(result.coverage, set)
    assert result.coverage == set()