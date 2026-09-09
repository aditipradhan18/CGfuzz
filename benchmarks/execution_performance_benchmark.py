from __future__ import annotations

import statistics
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

from src.executor import Executor, ExecutionStatus


# ============================================================
# CONFIGURATION
# ============================================================

ITERATIONS = 100

TARGET = PROJECT_ROOT / "src" / "target.py"

INPUTS = [
    b"",
    b"A",
    b"AB",
    b"B",
    b"BC",
    b"FUZZ",
    b"FUZZ1",
    b"FUZZ2",
    b"TEST",
    b"HELLO",
    b"CRASH",
]


# ============================================================
# BENCHMARK
# ============================================================

def run_benchmark() -> None:

    print("=" * 60)
    print("EXECUTION PERFORMANCE BENCHMARK")
    print("=" * 60)
    print(f"Target     : {TARGET}")
    print(f"Iterations : {ITERATIONS}")
    print("Execution  : Real subprocess Executor")
    print("=" * 60)

    if not TARGET.exists():
        print()
        print(f"[FAIL] Target not found: {TARGET}")
        return

    executor = Executor(
        target=TARGET,
        timeout=1.0,
    )

    execution_times = []

    normal_executions = 0
    crashes = 0
    timeouts = 0

    benchmark_start = time.perf_counter()

    for i in range(ITERATIONS):

        data = INPUTS[i % len(INPUTS)]

        result = executor.run(data)

        execution_times.append(result.duration)

        if result.status == ExecutionStatus.NORMAL:
            normal_executions += 1

        elif result.status == ExecutionStatus.CRASH:
            crashes += 1

        elif result.status == ExecutionStatus.TIMEOUT:
            timeouts += 1

        if (i + 1) % 20 == 0:

            elapsed = (
                time.perf_counter()
                - benchmark_start
            )

            rate = (
                (i + 1) / elapsed
                if elapsed > 0
                else 0.0
            )

            print(
                f"[Progress] "
                f"{i + 1}/{ITERATIONS} | "
                f"rate={rate:.2f} exec/sec"
            )

    benchmark_duration = (
        time.perf_counter()
        - benchmark_start
    )

    # ========================================================
    # METRICS
    # ========================================================

    executions = len(execution_times)

    execution_rate = (
        executions / benchmark_duration
        if benchmark_duration > 0
        else 0.0
    )

    average_execution_time = (
        statistics.mean(execution_times)
        if execution_times
        else 0.0
    )

    median_execution_time = (
        statistics.median(execution_times)
        if execution_times
        else 0.0
    )

    minimum_execution_time = (
        min(execution_times)
        if execution_times
        else 0.0
    )

    maximum_execution_time = (
        max(execution_times)
        if execution_times
        else 0.0
    )

    # ========================================================
    # RESULTS
    # ========================================================

    print()
    print("=" * 60)
    print("EXECUTION PERFORMANCE RESULTS")
    print("=" * 60)

    print(
        f"Executions            : "
        f"{executions}"
    )

    print(
        f"Normal executions     : "
        f"{normal_executions}"
    )

    print(
        f"Crashes               : "
        f"{crashes}"
    )

    print(
        f"Timeouts              : "
        f"{timeouts}"
    )

    print(
        f"Total benchmark time  : "
        f"{benchmark_duration:.2f} seconds"
    )

    print(
        f"Execution rate        : "
        f"{execution_rate:.2f} exec/sec"
    )

    print(
        f"Avg execution time    : "
        f"{average_execution_time * 1000:.2f} ms"
    )

    print(
        f"Median execution time : "
        f"{median_execution_time * 1000:.2f} ms"
    )

    print(
        f"Min execution time    : "
        f"{minimum_execution_time * 1000:.2f} ms"
    )

    print(
        f"Max execution time    : "
        f"{maximum_execution_time * 1000:.2f} ms"
    )

    print("=" * 60)

    # ========================================================
    # VALIDATION
    # ========================================================

    if executions != ITERATIONS:
        print(
            "[FAIL] Not all executions completed."
        )
        return

    if (
        normal_executions
        + crashes
        + timeouts
        != executions
    ):
        print(
            "[FAIL] Execution status accounting mismatch."
        )
        return

    if execution_rate <= 0:
        print(
            "[FAIL] Invalid execution rate."
        )
        return

    if average_execution_time <= 0:
        print(
            "[FAIL] Invalid execution timing."
        )
        return

    print(
        "[PASS] Execution performance benchmark"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_benchmark()