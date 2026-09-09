from __future__ import annotations

import sys
import time
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORT CGFUZZ
# ============================================================

from src.executor import Executor
from src.fuzzer import Fuzzer


# ============================================================
# CONFIGURATION
# ============================================================

ITERATIONS = 100
TARGET = PROJECT_ROOT / "src" / "target.py"
SEED = b"CRASH"


# ============================================================
# BENCHMARK
# ============================================================

def run_benchmark() -> None:

    print("=" * 70)
    print("CORPUS EFFICIENCY BENCHMARK")
    print("=" * 70)
    print(f"Target        : {TARGET}")
    print(f"Seed          : {SEED!r}")
    print(f"Iterations    : {ITERATIONS}")
    print("=" * 70)

    if not TARGET.exists():
        print()
        print(f"[FAIL] Target not found: {TARGET}")
        return

    executor = Executor(
        target=TARGET,
        timeout=1.0,
    )

    fuzzer = Fuzzer(
        executor=executor,
        iterations=ITERATIONS,
        max_input_size=4096,
        reproduction_attempts=3,
    )

    # --------------------------------------------------------
    # Run campaign
    # --------------------------------------------------------

    benchmark_start = time.perf_counter()

    fuzzer.run(SEED)

    duration = (
        time.perf_counter()
        - benchmark_start
    )

    # --------------------------------------------------------
    # Obtain campaign statistics
    # --------------------------------------------------------

    stats = fuzzer.get_statistics()

    executions = stats.get("executions", 0)
    coverage = stats.get("coverage_lines", 0)
    coverage_finds = stats.get("coverage_finds", 0)
    corpus_size = stats.get("corpus_size", 0)
    scheduler_entries = stats.get(
        "scheduler_entries",
        0,
    )
    crashes = stats.get("crashes", 0)

    # --------------------------------------------------------
    # Efficiency metrics
    # --------------------------------------------------------

    coverage_per_execution = (
        coverage / executions
        if executions > 0
        else 0.0
    )

    new_coverage_per_execution = (
        coverage_finds / executions
        if executions > 0
        else 0.0
    )

    corpus_growth = max(
        0,
        corpus_size - 1,
    )

    corpus_growth_rate = (
        corpus_growth / executions
        if executions > 0
        else 0.0
    )

    scheduler_ratio = (
        scheduler_entries / corpus_size
        if corpus_size > 0
        else 0.0
    )

    execution_rate = (
        executions / duration
        if duration > 0
        else 0.0
    )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CORPUS EFFICIENCY RESULTS")
    print("=" * 70)

    print(
        f"Executions                 : "
        f"{executions}"
    )

    print(
        f"Final corpus size          : "
        f"{corpus_size}"
    )

    print(
        f"Corpus growth              : "
        f"{corpus_growth}"
    )

    print(
        f"Scheduler entries          : "
        f"{scheduler_entries}"
    )

    print(
        f"Coverage lines             : "
        f"{coverage}"
    )

    print(
        f"Coverage discoveries       : "
        f"{coverage_finds}"
    )

    print(
        f"Crashes found              : "
        f"{crashes}"
    )

    print(
        f"Coverage / execution       : "
        f"{coverage_per_execution:.4f}"
    )

    print(
        f"New coverage / execution   : "
        f"{new_coverage_per_execution:.4f}"
    )

    print(
        f"Corpus growth / execution  : "
        f"{corpus_growth_rate:.4f}"
    )

    print(
        f"Scheduler / corpus ratio   : "
        f"{scheduler_ratio:.2%}"
    )

    print(
        f"Execution rate             : "
        f"{execution_rate:.2f} exec/sec"
    )

    print(
        f"Campaign duration          : "
        f"{duration:.2f} seconds"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    passed = (
        executions == ITERATIONS + 1
        and corpus_size >= 1
        and coverage >= 1
        and execution_rate > 0
    )

    if passed:
        print(
            "[PASS] Corpus efficiency benchmark"
        )
    else:
        print(
            "[FAIL] Corpus efficiency benchmark"
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_benchmark()