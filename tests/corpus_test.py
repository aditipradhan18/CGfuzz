from pathlib import Path

import pytest

from src.corpus import Corpus


def test_corpus_starts_empty(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    assert corpus.size() == 0
    assert len(corpus) == 0
    assert corpus.get_all() == []


def test_add_input(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    result = corpus.add(b"HELLO")

    assert result is True
    assert corpus.size() == 1
    assert b"HELLO" in corpus


def test_duplicate_input_is_not_added(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    assert corpus.add(b"HELLO") is True
    assert corpus.add(b"HELLO") is False

    assert corpus.size() == 1


def test_add_input_alias(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    result = corpus.add_input(
        b"TEST",
        {1, 2, 3}
    )

    assert result is True
    assert corpus.size() == 1


def test_get_all(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    corpus.add(b"ONE")
    corpus.add(b"TWO")
    corpus.add(b"THREE")

    inputs = corpus.get_all()

    assert inputs == [
        b"ONE",
        b"TWO",
        b"THREE"
    ]


def test_get_coverage(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    corpus.add(
        b"HELLO",
        {1, 2, 3}
    )

    coverage = corpus.get_coverage(b"HELLO")

    assert coverage == {1, 2, 3}


def test_get_coverage_unknown_input(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    coverage = corpus.get_coverage(
        b"UNKNOWN"
    )

    assert coverage == set()


def test_update_coverage_with_new_lines(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    corpus.add(
        b"HELLO",
        {1, 2}
    )

    changed = corpus.update_coverage(
        b"HELLO",
        {1, 2, 3, 4}
    )

    assert changed is True

    assert corpus.get_coverage(
        b"HELLO"
    ) == {1, 2, 3, 4}


def test_update_coverage_without_new_lines(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    corpus.add(
        b"HELLO",
        {1, 2, 3}
    )

    changed = corpus.update_coverage(
        b"HELLO",
        {1, 2, 3}
    )

    assert changed is False

    assert corpus.get_coverage(
        b"HELLO"
    ) == {1, 2, 3}


def test_update_coverage_unknown_input(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    changed = corpus.update_coverage(
        b"UNKNOWN",
        {1, 2, 3}
    )

    assert changed is False


def test_random_returns_existing_input(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    corpus.add(b"ONE")
    corpus.add(b"TWO")
    corpus.add(b"THREE")

    result = corpus.random()

    assert result in {
        b"ONE",
        b"TWO",
        b"THREE"
    }


def test_random_input_alias(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    corpus.add(b"HELLO")

    assert corpus.random_input() == b"HELLO"


def test_random_empty_corpus_raises(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    with pytest.raises(IndexError):
        corpus.random()


def test_directory_is_created(tmp_path):

    directory = tmp_path / "my_corpus"

    assert not directory.exists()

    Corpus(directory)

    assert directory.exists()
    assert directory.is_dir()


def test_bytes_conversion(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    corpus.add(bytearray(b"HELLO"))

    assert b"HELLO" in corpus


def test_iteration(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    corpus.add(b"ONE")
    corpus.add(b"TWO")

    assert list(corpus) == [
        b"ONE",
        b"TWO"
    ]


def test_repr(tmp_path):

    corpus = Corpus(tmp_path / "corpus")

    corpus.add(b"HELLO")

    representation = repr(corpus)

    assert "Corpus" in representation
    assert "size=1" in representation