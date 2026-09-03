from pathlib import Path

from src.executor import (
    Executor,
    ExecutionStatus
)


TARGET = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "src"
    / "target.py"
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