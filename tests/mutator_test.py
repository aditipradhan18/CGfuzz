from src.mutator import Mutator


def test_mutator_returns_bytes():

    mutator = Mutator()

    result = mutator.mutate(b"HELLO")

    assert isinstance(result, bytes)


def test_flip_bit_changes_input():

    mutator = Mutator()

    original = b"HELLO"

    result = mutator.flip_bit(original)

    assert isinstance(result, bytes)
    assert len(result) == len(original)
    assert result != original


def test_flip_byte_changes_input():

    mutator = Mutator()

    original = b"HELLO"

    result = mutator.flip_byte(original)

    assert isinstance(result, bytes)
    assert len(result) == len(original)
    assert result != original


def test_insert_byte_increases_size():

    mutator = Mutator()

    original = b"HELLO"

    result = mutator.insert_byte(original)

    assert len(result) == len(original) + 1


def test_delete_byte_decreases_size():

    mutator = Mutator()

    original = b"HELLO"

    result = mutator.delete_byte(original)

    assert len(result) == len(original) - 1


def test_replace_byte_preserves_size():

    mutator = Mutator()

    original = b"HELLO"

    result = mutator.replace_byte(original)

    assert len(result) == len(original)
    assert isinstance(result, bytes)


def test_arithmetic_mutation_preserves_size():

    mutator = Mutator()

    original = b"HELLO"

    result = mutator.arithmetic_mutation(original)

    assert len(result) == len(original)
    assert isinstance(result, bytes)


def test_empty_input_can_be_mutated():

    mutator = Mutator()

    result = mutator.mutate(b"")

    assert isinstance(result, bytes)
    assert len(result) == 1


def test_empty_input_insertion():

    mutator = Mutator()

    result = mutator.insert_byte(b"")

    assert len(result) == 1


def test_empty_input_deletion():

    mutator = Mutator()

    result = mutator.delete_byte(b"")

    assert result == b""


def test_max_size_is_respected():

    mutator = Mutator(max_size=5)

    original = b"12345"

    result = mutator.insert_byte(original)

    assert len(result) <= 5


def test_mutate_n():

    mutator = Mutator()

    original = b"HELLO"

    result = mutator.mutate_n(
        original,
        count=5
    )

    assert isinstance(result, bytes)


def test_mutate_n_zero():

    mutator = Mutator()

    original = b"HELLO"

    result = mutator.mutate_n(
        original,
        count=0
    )

    assert result == original


def test_mutate_n_multiple():

    mutator = Mutator()

    original = b"HELLO"

    result = mutator.mutate_n(
        original,
        count=10
    )

    assert isinstance(result, bytes)
    assert len(result) <= mutator.max_size