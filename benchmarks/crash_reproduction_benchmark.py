from __future__ import annotations

import time
from pathlib import Path

from src.executor import Executor
from src.crash_reproducer import CrashReproducer


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TARGET = PROJECT_ROOT / "src" / "target.py"

CRASHING_INPUT = b"CRASH"

REPRODUCTION_ATTEMPTS = 10


# ============================================================
# BENCHMARK
# ============================================================

def run_benchmark() -> None:

    print("=" * 60)
    print("CRASH REPRODUCTION BENCHMARK")
    print("=" * 60)

    print(
        f"Target              : {TARGET}"
    )

    print(
        f"Crash input         : {CRASHING_INPUT!r}"
    )

    print(
        f"Reproduction runs   : {REPRODUCTION_ATTEMPTS}"
    )

    print("=" * 60)

    if not TARGET.exists():
        print(
            f"[FAIL] Target not found: {TARGET}"
        )
        return

    # --------------------------------------------------------
    # Executor
    # --------------------------------------------------------

    executor = Executor(
        target=TARGET,
        timeout=1.0,
    )

    # --------------------------------------------------------
    # Reproducer
    # --------------------------------------------------------

    reproducer = CrashReproducer(
        executor=executor,
        attempts=REPRODUCTION_ATTEMPTS,
    )

    # --------------------------------------------------------
    # Run reproduction benchmark
    # --------------------------------------------------------

    print()
    print(
        "[*] Re-running crashing input..."
    )

    start = time.perf_counter()

    result = reproducer.reproduce(
        CRASHING_INPUT
    )

    duration = (
        time.perf_counter() - start
    )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("CRASH REPRODUCTION RESULTS")
    print("=" * 60)

    print(
        f"Attempts            : "
        f"{result.attempts}"
    )

    print(
        f"Crashes             : "
        f"{result.crashes}"
    )

    print(
        f"Normal executions   : "
        f"{result.normal}"
    )

    print(
        f"Timeouts            : "
        f"{result.timeouts}"
    )

    print(
        f"Reproduced          : "
        f"{result.reproduced}"
    )

    print(
        f"Total time          : "
        f"{duration:.4f} seconds"
    )

    if result.attempts > 0:
        reproduction_rate = (
            result.crashes
            / result.attempts
        ) * 100
    else:
        reproduction_rate = 0.0

    print(
        f"Reproduction rate   : "
        f"{reproduction_rate:.2f}%"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if not result.reproduced:
        print(
            "[FAIL] Crash could not be reproduced."
        )
        return

    if result.crashes != result.attempts:
        print(
            "[FAIL] Crash was not reproduced "
            "on every attempt."
        )
        return

    if result.normal != 0:
        print(
            "[FAIL] Some executions completed normally."
        )
        return

    if result.timeouts != 0:
        print(
            "[FAIL] Some executions timed out."
        )
        return

    print(
        "[PASS] Crash reproduction benchmark"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_benchmark()