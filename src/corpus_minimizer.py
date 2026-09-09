"""
Corpus minimization using greedy set cover.

Keeps a small subset of corpus inputs that collectively
preserves the discovered coverage.
"""

from dataclasses import dataclass
from typing import Iterable


@dataclass
class MinimizedCorpus:
    """Result returned by corpus minimization."""

    inputs: list[bytes]
    coverage: set


class CorpusMinimizer:
    """
    Reduce a corpus using a greedy set-cover algorithm.

    Each input is associated with a set of coverage identifiers.
    The minimizer repeatedly selects the input that contributes
    the most previously uncovered coverage.
    """

    def minimize(
        self,
        inputs: Iterable[bytes],
        coverage: Iterable[Iterable],
    ) -> MinimizedCorpus:
        """
        Minimize inputs while preserving their combined coverage.

        Args:
            inputs:
                Corpus input bytes.

            coverage:
                Coverage set corresponding to each input.

        Returns:
            MinimizedCorpus containing the selected inputs
            and their combined coverage.
        """

        inputs = list(inputs)

        coverage = [
            set(item)
            for item in coverage
        ]

        if len(inputs) != len(coverage):
            raise ValueError(
                "inputs and coverage must have the same length"
            )

        if not inputs:
            return MinimizedCorpus(
                inputs=[],
                coverage=set(),
            )

        # Collect every coverage point that must be preserved.
        remaining = set()

        for item in coverage:
            remaining.update(item)

        selected_inputs = []
        selected_indexes = set()
        preserved_coverage = set()

        # Greedy set-cover selection.
        while remaining:

            best_index = None
            best_new_coverage = set()

            for index, item_coverage in enumerate(coverage):

                if index in selected_indexes:
                    continue

                new_coverage = (
                    item_coverage &
                    remaining
                )

                if len(new_coverage) > len(
                    best_new_coverage
                ):
                    best_index = index
                    best_new_coverage = new_coverage

            # No remaining input can contribute coverage.
            if best_index is None:
                break

            selected_indexes.add(best_index)

            selected_inputs.append(
                inputs[best_index]
            )

            preserved_coverage.update(
                coverage[best_index]
            )

            remaining.difference_update(
                best_new_coverage
            )

        return MinimizedCorpus(
            inputs=selected_inputs,
            coverage=preserved_coverage,
        )