from src.sanitizer import (
    Sanitizer,
    SanitizationStatus,
)


def test_accepts_normal_bytes():
    sanitizer = Sanitizer()

    result = sanitizer.sanitize(b"HELLO")

    assert result.status == SanitizationStatus.ACCEPTED
    assert result.data == b"HELLO"
    assert result.accepted


def test_accepts_empty_input():
    sanitizer = Sanitizer()

    result = sanitizer.sanitize(b"")

    assert result.status == SanitizationStatus.ACCEPTED
    assert result.data == b""


def test_accepts_binary_data():
    sanitizer = Sanitizer()

    data = b"\x00\xff\x01\xfe"

    result = sanitizer.sanitize(data)

    assert result.status == SanitizationStatus.ACCEPTED
    assert result.data == data


def test_rejects_non_bytes():
    sanitizer = Sanitizer()

    result = sanitizer.sanitize("HELLO")

    assert result.status == SanitizationStatus.REJECTED
    assert not result.accepted


def test_rejects_oversized_input():
    sanitizer = Sanitizer(
        max_input_size=4
    )

    result = sanitizer.sanitize(b"12345")

    assert result.status == SanitizationStatus.REJECTED
    assert not result.accepted


def test_accepts_input_at_maximum_size():
    sanitizer = Sanitizer(
        max_input_size=4
    )

    result = sanitizer.sanitize(b"1234")

    assert result.status == SanitizationStatus.ACCEPTED
    assert result.data == b"1234"


def test_is_safe():
    sanitizer = Sanitizer(
        max_input_size=10
    )

    assert sanitizer.is_safe(b"HELLO")
    assert not sanitizer.is_safe(b"12345678901")