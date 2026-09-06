from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORT
# ============================================================

from src.coverage_guided import CoverageGuidedScheduler


# ============================================================
# CONFIGURATION
# ============================================================

SELECTIONS = 1000
RANDOM_SEED = 42


# ============================================================
# BENCHMARK CORPUS
# ============================================================

CORPUS_ENTRIES = [
    (b"SEED_A", {1, 2}),
    (b"SEED_B", {3, 4, 5, 6}),
    (b"SEED_C", {7, 8, 9, 10, 11, 12}),
    (b"SEED_D", {13, 14, 15, 16, 17, 18, 19, 20}),
]


# ============================================================
# CREATE SCHEDULER
# ============================================================

def create_scheduler() -> CoverageGuidedScheduler:
    """
    Create a deterministic coverage-guided scheduler.

    Supports both the current random_seed argument and the
    older seed argument for compatibility.
    """

    try:
        return CoverageGuidedScheduler(
            random_seed=RANDOM_SEED
        )

    except TypeError:
        return CoverageGuidedScheduler(
            seed=RANDOM_SEED
        )


# ============================================================
# POPULATE SCHEDULER
# ============================================================

def populate_scheduler(
    scheduler: CoverageGuidedScheduler,
) -> None:
    """
    Add benchmark inputs and their coverage information
    to the scheduler.
    """

    for data, coverage in CORPUS_ENTRIES:
        scheduler.add(
            data,
            coverage
        )


# ============================================================
# SINGLE SELECTION TEST
# ============================================================

def test_selection(
    scheduler: CoverageGuidedScheduler,
) -> bool:
    """
    Verify that the scheduler can select an input.

    The scheduler maintains its own corpus, so select()
    requires no input argument.
    """

    try:
        selected = scheduler.select()

    except Exception as error:
        print(
            f"[FAIL] Scheduler selection failed: {error}"
        )
        return False

    valid_inputs = {
        data
        for data, _ in CORPUS_ENTRIES
    }

    if selected not in valid_inputs:
        print(
            "[FAIL] Scheduler returned an unknown input."
        )
        print(
            f"[FAIL] Selected: {selected!r}"
        )
        return False

    return True


# ============================================================
# RUN SELECTION BENCHMARK
# ============================================================

def run_selection_benchmark(
    scheduler: CoverageGuidedScheduler,
) -> tuple[Counter, float]:
    """
    Perform repeated scheduler selections.

    Returns:
        selection counts
        total selection time
    """

    counts = Counter()

    start = time.perf_counter()

    for _ in range(SELECTIONS):

        # IMPORTANT:
        # CoverageGuidedScheduler.select() takes no arguments.
        selected = scheduler.select()

        counts[selected] += 1

    duration = (
        time.perf_counter()
        - start
    )

    return counts, duration


# ============================================================
# PRINT DISTRIBUTION
# ============================================================

def print_distribution(
    counts: Counter,
) -> None:
    """
    Print the selection frequency of every corpus entry.
    """

    print()
    print(
        "SELECTION DISTRIBUTION"
    )
    print(
        "-" * 60
    )

    for data, coverage in CORPUS_ENTRIES:

        count = counts.get(
            data,
            0
        )

        percentage = (
            count
            / SELECTIONS
            * 100.0
        )

        print(
            f"{data!r:<14}"
            f" coverage={len(coverage):<3}"
            f" selections={count:<5}"
            f" ({percentage:6.2f}%)"
        )


# ============================================================
# FIND MOST SELECTED INPUT
# ============================================================

def get_most_selected(
    counts: Counter,
) -> tuple[bytes, int, float]:
    """
    Return the most frequently selected corpus entry.
    """

    if not counts:
        return b"", 0, 0.0

    data, count = counts.most_common(1)[0]

    percentage = (
        count
        / SELECTIONS
        * 100.0
    )

    return (
        data,
        count,
        percentage,
    )


# ============================================================
# BENCHMARK
# ============================================================

def run_benchmark() -> None:

    print()
    print(
        "=" * 60
    )
    print(
        "SCHEDULER BENCHMARK"
    )
    print(
        "=" * 60
    )

    print(
        f"Corpus entries : {len(CORPUS_ENTRIES)}"
    )

    print(
        f"Selections     : {SELECTIONS}"
    )

    print(
        f"Random seed    : {RANDOM_SEED}"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # CREATE
    # --------------------------------------------------------

    scheduler = create_scheduler()

    # --------------------------------------------------------
    # POPULATE
    # --------------------------------------------------------

    populate_scheduler(
        scheduler
    )

    print()
    print(
        f"Scheduler entries: "
        f"{len(CORPUS_ENTRIES)}"
    )

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    if not test_selection(
        scheduler
    ):
        print()
        print(
            "[FAIL] Scheduler benchmark"
        )
        return

    print(
        "[PASS] Scheduler selection is functional."
    )

    # --------------------------------------------------------
    # BENCHMARK
    # --------------------------------------------------------

    counts, duration = run_selection_benchmark(
        scheduler
    )

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    selection_rate = (
        SELECTIONS / duration
        if duration > 0
        else 0.0
    )

    most_selected, most_count, most_percentage = (
        get_most_selected(
            counts
        )
    )

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    print()
    print(
        "=" * 60
    )
    print(
        "SCHEDULER RESULTS"
    )
    print(
        "=" * 60
    )

    print(
        f"Selections           : {SELECTIONS}"
    )

    print(
        f"Scheduler time       : "
        f"{duration:.6f} seconds"
    )

    print(
        f"Selection rate       : "
        f"{selection_rate:.2f} selections/sec"
    )

    print(
        f"Most selected input  : "
        f"{most_selected!r}"
    )

    print(
        f"Most selected count  : "
        f"{most_count}"
    )

    print(
        f"Selection percentage: "
        f"{most_percentage:.2f}%"
    )

    # --------------------------------------------------------
    # DISTRIBUTION
    # --------------------------------------------------------

    print_distribution(
        counts
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    expected_inputs = {
        data
        for data, _ in CORPUS_ENTRIES
    }

    selected_inputs = set(
        counts.keys()
    )

    all_inputs_reachable = (
        selected_inputs
        == expected_inputs
    )

    highest_coverage_input = max(
        CORPUS_ENTRIES,
        key=lambda item: len(item[1])
    )[0]

    highest_coverage_count = counts.get(
        highest_coverage_input,
        0
    )

    highest_coverage_reachable = (
        highest_coverage_count > 0
    )

    print()
    print(
        "=" * 60
    )

    if (
        all_inputs_reachable
        and highest_coverage_reachable
        and len(counts) == len(CORPUS_ENTRIES)
    ):
        print(
            "[PASS] Scheduler benchmark"
        )

    else:
        print(
            "[FAIL] Scheduler benchmark"
        )

        if not all_inputs_reachable:
            print(
                "[!] Not all corpus entries were selected."
            )

        if not highest_coverage_reachable:
            print(
                "[!] Highest-coverage entry was never selected."
            )

    print(
        "=" * 60
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_benchmark()