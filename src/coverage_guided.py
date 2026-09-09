from __future__ import annotations

import random

from dataclasses import dataclass
from typing import Iterable

from .bitmap import CoverageBitmap


@dataclass
class CorpusEntry:
    """
    Represents one input in the fuzzing corpus.

    Each entry contains:
        data     -> actual input bytes
        coverage -> line/edge coverage identifiers
        bitmap   -> optional bitmap representation of edge coverage
    """

    data: bytes
    coverage: set
    bitmap: CoverageBitmap | None = None


class CoverageGuidedScheduler:
    """
    Coverage-guided input scheduler.

    Inputs that discover more coverage receive higher
    scheduling priority.

    Smaller inputs receive a small bonus because they
    are generally cheaper to execute.

    Bitmap coverage is used when available to provide
    edge-level coverage information.
    """

    def __init__(
        self,
        seed: bytes | None = None,
        random_seed: int | None = None
    ):
        self.entries: list[CorpusEntry] = []

        # Line/edge coverage identifiers.
        self.total_coverage: set = set()

        # Global edge bitmap.
        self.total_bitmap = CoverageBitmap()

        self.random = random.Random(
            random_seed
        )

        if seed is not None:
            self.add(
                seed,
                set()
            )

    # =========================================================
    # ADD INPUT
    # =========================================================

    def add(
        self,
        data: bytes,
        coverage: Iterable,
        bitmap: CoverageBitmap | None = None
    ) -> bool:
        """
        Add an input when it discovers new coverage.

        Returns True if new line/edge or bitmap coverage
        was discovered.
        """

        if not isinstance(data, bytes):
            data = bytes(data)

        coverage = set(coverage)

        # Determine new line/edge coverage.
        new_coverage = (
            coverage -
            self.total_coverage
        )

        # Determine new bitmap coverage.
        new_bitmap = False

        if bitmap is not None:
            if not isinstance(bitmap, CoverageBitmap):
                raise TypeError(
                    "bitmap must be a CoverageBitmap"
                )

            # Check whether the bitmap contains any
            # previously unseen bitmap slots.
            for i in range(bitmap.size):
                if (
                    bitmap.bitmap[i] != 0
                    and self.total_bitmap.bitmap[i] == 0
                ):
                    new_bitmap = True
                    break

        # Do not add an input that discovers nothing new.
        if not new_coverage and not new_bitmap:
            return False

        entry = CorpusEntry(
            data=data,
            coverage=coverage,
            bitmap=(
                bitmap.copy()
                if bitmap is not None
                else None
            )
        )

        self.entries.append(entry)

        self.total_coverage.update(
            new_coverage
        )

        if bitmap is not None:
            self.total_bitmap.merge(bitmap)

        return True

    # =========================================================
    # ADD ENTRY
    # =========================================================

    def add_entry(
        self,
        entry: CorpusEntry
    ) -> bool:
        """
        Add an existing CorpusEntry.
        """

        return self.add(
            entry.data,
            entry.coverage,
            entry.bitmap
        )

    # =========================================================
    # SCORE
    # =========================================================

    def score(
        self,
        entry: CorpusEntry
    ) -> float:
        """
        Calculate the scheduling score.

        More coverage = higher score.

        Bitmap edge coverage contributes to the score
        when available.

        Smaller input = small additional bonus.
        """

        coverage_score = len(
            entry.coverage
        )

        bitmap_score = 0

        if entry.bitmap is not None:
            bitmap_score = entry.bitmap.hit_count()

        size = max(
            len(entry.data),
            1
        )

        size_bonus = 1.0 / size

        return (
            float(coverage_score) +
            float(bitmap_score) +
            size_bonus
        )

    # =========================================================
    # GET SCORES
    # =========================================================

    def scores(self) -> list[float]:
        """
        Return scores for all entries.
        """

        return [
            self.score(entry)
            for entry in self.entries
        ]

    # =========================================================
    # BEST INPUT
    # =========================================================

    def best(self) -> bytes:
        """
        Return the highest-scoring input.
        """

        if not self.entries:
            raise IndexError(
                "CoverageGuidedScheduler is empty"
            )

        best_entry = max(
            self.entries,
            key=self.score
        )

        return best_entry.data

    # =========================================================
    # SELECT INPUT
    # =========================================================

    def select(self) -> bytes:
        """
        Select an input using coverage-weighted
        random selection.

        High-value inputs are more likely to be selected,
        while lower-value inputs can still be explored.
        """

        if not self.entries:
            raise IndexError(
                "CoverageGuidedScheduler is empty"
            )

        weights = [
            max(
                self.score(entry),
                0.000001
            )
            for entry in self.entries
        ]

        selected = self.random.choices(
            self.entries,
            weights=weights,
            k=1
        )[0]

        return selected.data

    # =========================================================
    # RANDOM INPUT
    # =========================================================

    def random_input(self) -> bytes:
        """
        Select a completely random corpus input.
        """

        if not self.entries:
            raise IndexError(
                "CoverageGuidedScheduler is empty"
            )

        return self.random.choice(
            self.entries
        ).data

    # =========================================================
    # GET ENTRY
    # =========================================================

    def get_entry(
        self,
        data: bytes
    ) -> CorpusEntry:
        """
        Find an entry by its input bytes.
        """

        for entry in self.entries:
            if entry.data == data:
                return entry

        raise KeyError(
            "Input not found in scheduler"
        )

    # =========================================================
    # HAS INPUT
    # =========================================================

    def contains(
        self,
        data: bytes
    ) -> bool:
        """
        Return True if the input exists.
        """

        return any(
            entry.data == data
            for entry in self.entries
        )

    # =========================================================
    # COVERAGE
    # =========================================================

    def coverage_size(self) -> int:
        """
        Return total unique coverage.
        """

        return len(
            self.total_coverage
        )

    # =========================================================
    # BITMAP COVERAGE
    # =========================================================

    def bitmap_coverage_size(self) -> int:
        """
        Return the number of globally discovered
        bitmap coverage slots.
        """

        return self.total_bitmap.hit_count()

    # =========================================================
    # CORPUS SIZE
    # =========================================================

    def size(self) -> int:
        """
        Return number of scheduled inputs.
        """

        return len(
            self.entries
        )

    # =========================================================
    # EMPTY
    # =========================================================

    def is_empty(self) -> bool:
        """
        Return True if scheduler contains no inputs.
        """

        return len(
            self.entries
        ) == 0

    # =========================================================
    # CLEAR
    # =========================================================

    def clear(self):
        """
        Remove all inputs and reset coverage.
        """

        self.entries.clear()
        self.total_coverage.clear()
        self.total_bitmap.reset()

    # =========================================================
    # ITERATION
    # =========================================================

    def __iter__(self):
        """
        Allow:

            for entry in scheduler:
                ...
        """

        return iter(
            self.entries
        )

    # =========================================================
    # LENGTH
    # =========================================================

    def __len__(self):
        """
        Allow:

            len(scheduler)
        """

        return len(
            self.entries
        )

    # =========================================================
    # CONTAINS
    # =========================================================

    def __contains__(
        self,
        data: bytes
    ):
        """
        Allow:

            data in scheduler
        """

        return self.contains(
            data
        )

    # =========================================================
    # REPRESENTATION
    # =========================================================

    def __repr__(self):
        return (
            "CoverageGuidedScheduler("
            f"entries={len(self.entries)}, "
            f"coverage={len(self.total_coverage)}, "
            f"bitmap={self.total_bitmap.hit_count()}"
            ")"
        )