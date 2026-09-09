from src.corpus_minimizer import CorpusMinimizer


def test_minimize_preserves_all_coverage():
    inputs = [
        b"A",
        b"B",
        b"C",
        b"D",
    ]

    coverage = [
        {1, 2},
        {2, 3},
        {4},
        {1, 3, 4},
    ]

    result = CorpusMinimizer().minimize(
        inputs,
        coverage,
    )

    assert set(result.coverage) == {
        1,
        2,
        3,
        4,
    }

    assert len(result.inputs) == 2


def test_empty_corpus():
    result = CorpusMinimizer().minimize(
        [],
        [],
    )

    assert result.inputs == []
    assert result.coverage == set()


def test_empty_coverage():
    result = CorpusMinimizer().minimize(
        [b"A", b"B"],
        [set(), set()],
    )

    assert result.inputs == []
    assert result.coverage == set()


def test_mismatched_lengths():
    try:
        CorpusMinimizer().minimize(
            [b"A"],
            [{1}, {2}],
        )

        assert False

    except ValueError:
        assert True