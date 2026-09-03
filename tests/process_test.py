from src.executor import Executor


executor = Executor(
    target="src/target.py",
    timeout=1.0
)


def test_normal_execution():
    result = executor.run(b"HELLO")

    assert result is not None


def test_crash_execution():
    result = executor.run(b"CRASH")

    assert result is not None


def test_empty_input():
    result = executor.run(b"")

    assert result is not None