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
# IMPORTS
# ============================================================

from src.executor import Executor, ExecutionStatus
from src.crash_minimizer import CrashMinimizer


# ============================================================
# CONFIGURATION
# ============================================================

TARGET = PROJECT_ROOT / "src" / "target.py"

ORIGINAL_INPUT = (
    b"XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    b"CRASH"
    b"XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
)

TIMEOUT = 1.0


# ============================================================
# HELPERS
# ============================================================

def execute_target(
    executor: Executor,
    data: bytes,
):
    """
    Execute an input and return the execution result.
    """

    return executor.run(data)


def is_crashing(
    executor: Executor,
    data: bytes,
) -> bool:
    """
    Determine whether an input still produces a crash.
    """

    result = execute_target(
        executor,
        data,
    )

    return result.status == ExecutionStatus.CRASH


# ============================================================
# BENCHMARK
# ============================================================

def run_benchmark() -> None:
    print()
    print("=" * 60)
    print("CRASH MINIMIZATION BENCHMARK")
    print("=" * 60)

    print(
        f"Target         : {TARGET}"
    )

    print(
        f"Original input : {ORIGINAL_INPUT!r}"
    )

    print(
        f"Original size  : {len(ORIGINAL_INPUT)} bytes"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # CREATE EXECUTOR
    # --------------------------------------------------------

    executor = Executor(
        target=TARGET,
        timeout=TIMEOUT,
    )

    # --------------------------------------------------------
    # VERIFY ORIGINAL CRASH
    # --------------------------------------------------------

    original_result = execute_target(
        executor,
        ORIGINAL_INPUT,
    )

    if original_result.status != ExecutionStatus.CRASH:
        print()
        print(
            "[FAIL] Original input does not produce a crash."
        )
        print(
            f"Status: {original_result.status}"
        )
        return

    print()
    print(
        "[PASS] Original input produces a crash."
    )

    # --------------------------------------------------------
    # CREATE MINIMIZER
    # --------------------------------------------------------

    minimizer = CrashMinimizer(
        executor=executor,
    )

    # --------------------------------------------------------
    # MINIMIZE
    # --------------------------------------------------------

    print()
    print(
        "[*] Minimizing crash..."
    )

    start = time.perf_counter()

    minimized = minimizer.minimize(
        ORIGINAL_INPUT
    )

    duration = (
        time.perf_counter()
        - start
    )

    # --------------------------------------------------------
    # VERIFY MINIMIZED INPUT
    # --------------------------------------------------------

    minimized_result = execute_target(
        executor,
        minimized,
    )

    minimized_crashes = (
        minimized_result.status
        == ExecutionStatus.CRASH
    )

    # --------------------------------------------------------
    # CALCULATE METRICS
    # --------------------------------------------------------

    original_size = len(
        ORIGINAL_INPUT
    )

    minimized_size = len(
        minimized
    )

    bytes_removed = (
        original_size
        - minimized_size
    )

    if original_size > 0:
        size_reduction = (
            bytes_removed
            / original_size
            * 100.0
        )
    else:
        size_reduction = 0.0

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("CRASH MINIMIZATION RESULTS")
    print("=" * 60)

    print(
        f"Original input   : {ORIGINAL_INPUT!r}"
    )

    print(
        f"Original size    : {original_size} bytes"
    )

    print(
        f"Minimized input  : {minimized!r}"
    )

    print(
        f"Minimized size   : {minimized_size} bytes"
    )

    print(
        f"Bytes removed    : {bytes_removed}"
    )

    print(
        f"Size reduction   : {size_reduction:.2f}%"
    )

    print(
        f"Minimization time: {duration:.4f} seconds"
    )

    print(
        f"Crash preserved  : {minimized_crashes}"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # VALIDATE RESULT
    # --------------------------------------------------------

    if not minimized_crashes:
        print(
            "[FAIL] Minimization lost the crash."
        )
        return

    if minimized_size > original_size:
        print(
            "[FAIL] Minimized input is larger than original."
        )
        return

    print(
        "[PASS] Crash minimization benchmark"
    )

    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_benchmark()