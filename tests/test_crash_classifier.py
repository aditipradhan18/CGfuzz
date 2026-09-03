import pytest

from src.crash_classifier import (
    CrashClassifier,
    CrashClassification,
    CrashType,
)
from src.executor import ExecutionResult, ExecutionStatus


@pytest.fixture
def classifier():
    return CrashClassifier()


# =========================================================
# EXCEPTION CLASSIFICATION
# =========================================================


def test_runtime_error(classifier):
    error = RuntimeError("test crash")

    result = classifier.classify_exception(error)

    assert result.crash_type == CrashType.RUNTIME_ERROR
    assert result.name == "RuntimeError"
    assert result.message == "test crash"


def test_value_error(classifier):
    error = ValueError("invalid value")

    result = classifier.classify_exception(error)

    assert result.crash_type == CrashType.VALUE_ERROR
    assert result.message == "invalid value"


def test_type_error(classifier):
    error = TypeError("wrong type")

    result = classifier.classify_exception(error)

    assert result.crash_type == CrashType.TYPE_ERROR


def test_index_error(classifier):
    error = IndexError("out of range")

    result = classifier.classify_exception(error)

    assert result.crash_type == CrashType.INDEX_ERROR


def test_key_error(classifier):
    error = KeyError("missing key")

    result = classifier.classify_exception(error)

    assert result.crash_type == CrashType.KEY_ERROR


def test_attribute_error(classifier):
    error = AttributeError("missing attribute")

    result = classifier.classify_exception(error)

    assert result.crash_type == CrashType.ATTRIBUTE_ERROR


def test_zero_division_error(classifier):
    error = ZeroDivisionError("division by zero")

    result = classifier.classify_exception(error)

    assert result.crash_type == CrashType.ZERO_DIVISION


def test_memory_error(classifier):
    error = MemoryError("out of memory")

    result = classifier.classify_exception(error)

    assert result.crash_type == CrashType.MEMORY_ERROR


def test_assertion_error(classifier):
    error = AssertionError("assertion failed")

    result = classifier.classify_exception(error)

    assert result.crash_type == CrashType.ASSERTION_ERROR


# =========================================================
# UNKNOWN EXCEPTION
# =========================================================


def test_unknown_exception(classifier):
    class CustomError(Exception):
        pass

    error = CustomError("custom failure")

    result = classifier.classify_exception(error)

    assert result.crash_type == CrashType.UNKNOWN
    assert result.message == "custom failure"


# =========================================================
# STDERR CLASSIFICATION
# =========================================================


def test_classify_runtime_error_stderr(classifier):
    stderr = (
        b"Traceback (most recent call last):\n"
        b"RuntimeError: Intentional fuzzing crash\n"
    )

    result = classifier.classify_stderr(stderr)

    assert result.crash_type == CrashType.RUNTIME_ERROR
    assert result.message == "Intentional fuzzing crash"


def test_classify_value_error_stderr(classifier):
    stderr = b"ValueError: invalid input\n"

    result = classifier.classify_stderr(stderr)

    assert result.crash_type == CrashType.VALUE_ERROR
    assert result.message == "invalid input"


def test_classify_type_error_stderr(classifier):
    stderr = b"TypeError: wrong operand type\n"

    result = classifier.classify_stderr(stderr)

    assert result.crash_type == CrashType.TYPE_ERROR
    assert result.message == "wrong operand type"


def test_classify_index_error_stderr(classifier):
    stderr = b"IndexError: list index out of range\n"

    result = classifier.classify_stderr(stderr)

    assert result.crash_type == CrashType.INDEX_ERROR
    assert result.message == "list index out of range"


def test_classify_unknown_stderr(classifier):
    stderr = b"Something unexpected happened"

    result = classifier.classify_stderr(stderr)

    assert result.crash_type == CrashType.UNKNOWN
    assert result.message == "Something unexpected happened"


def test_empty_stderr(classifier):
    result = classifier.classify_stderr(b"")

    assert result.crash_type == CrashType.UNKNOWN
    assert result.message == ""


# =========================================================
# STRING STDERR
# =========================================================


def test_string_stderr(classifier):
    stderr = "RuntimeError: crash message"

    result = classifier.classify_stderr(stderr)

    assert result.crash_type == CrashType.RUNTIME_ERROR
    assert result.message == "crash message"


# =========================================================
# EXECUTION RESULT
# =========================================================


def test_classify_execution_result(classifier):
    execution = ExecutionResult(
        status=ExecutionStatus.CRASH,
        exit_code=1,
        stderr=b"RuntimeError: target crashed",
    )

    result = classifier.classify(execution)

    assert result.crash_type == CrashType.RUNTIME_ERROR
    assert result.message == "target crashed"


def test_classify_execution_result_unknown(classifier):
    execution = ExecutionResult(
        status=ExecutionStatus.CRASH,
        exit_code=1,
        stderr=b"unknown failure",
    )

    result = classifier.classify(execution)

    assert result.crash_type == CrashType.UNKNOWN


# =========================================================
# HELPERS
# =========================================================


def test_is_known(classifier):
    result = classifier.classify_stderr(
        b"RuntimeError: crash"
    )

    assert classifier.is_known(result) is True


def test_unknown_is_not_known(classifier):
    result = classifier.classify_stderr(
        b"unknown failure"
    )

    assert classifier.is_known(result) is False


def test_get_type(classifier):
    result = classifier.classify_stderr(
        b"ValueError: bad value"
    )

    assert classifier.get_type(result) == "ValueError"


def test_get_message(classifier):
    result = classifier.classify_stderr(
        b"RuntimeError: crash happened"
    )

    assert classifier.get_message(result) == "crash happened"


# =========================================================
# REPRESENTATION
# =========================================================


def test_classification_repr():
    result = CrashClassification(
        CrashType.RUNTIME_ERROR,
        "test crash"
    )

    representation = repr(result)

    assert "RuntimeError" in representation
    assert "test crash" in representation