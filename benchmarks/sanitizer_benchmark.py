from __future__ import annotations

import sys
import time
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.sanitizer import Sanitizer, SanitizationStatus


# ============================================================
# CONFIGURATION
# ============================================================

TOTAL_INPUTS = 1000
MAX_INPUT_SIZE = 64


# ============================================================
# TEST INPUT GENERATION
# ============================================================

def generate_inputs() -> list[bytes]:
    """
    Generate a deterministic benchmark workload.

    Half of the inputs are within the allowed size limit.
    Half exceed the configured maximum size and should be
    rejected by the sanitizer.
    """

    inputs: list[bytes] = []

    for i in range(TOTAL_INPUTS // 2):
        size = 1 + (i % MAX_INPUT_SIZE)
        inputs.append(
            bytes([65 + (i % 26)]) * size
        )

    for i in range(TOTAL_INPUTS // 2):
        size = MAX_INPUT_SIZE + 1 + (i % 64)
        inputs.append(
            bytes([97 + (i % 26)]) * size
        )

    return inputs


# ============================================================
# BENCHMARK
# ============================================================

def run_benchmark() -> None:
    print("=" * 60)
    print("SANITIZER BENCHMARK")
    print("=" * 60)

    print(f"Total inputs        : {TOTAL_INPUTS}")
    print(f"Maximum input size  : {MAX_INPUT_SIZE} bytes")
    print("=" * 60)

    sanitizer = Sanitizer(
        max_input_size=MAX_INPUT_SIZE
    )

    inputs = generate_inputs()

    accepted = 0
    rejected = 0
    unexpected = 0

    start = time.perf_counter()

    for index, data in enumerate(inputs, start=1):

        result = sanitizer.sanitize(data)

        if result.status == SanitizationStatus.ACCEPTED:
            accepted += 1

        elif result.status == SanitizationStatus.REJECTED:
            rejected += 1

        else:
            unexpected += 1

        if index % 200 == 0:
            elapsed = time.perf_counter() - start

            rate = (
                index / elapsed
                if elapsed > 0
                else 0.0
            )

            print(
                f"[Progress] "
                f"{index}/{TOTAL_INPUTS} | "
                f"rate={rate:.2f} inputs/sec"
            )

    duration = time.perf_counter() - start

    rate = (
        TOTAL_INPUTS / duration
        if duration > 0
        else 0.0
    )

    accepted_percentage = (
        accepted / TOTAL_INPUTS * 100
        if TOTAL_INPUTS > 0
        else 0.0
    )

    rejected_percentage = (
        rejected / TOTAL_INPUTS * 100
        if TOTAL_INPUTS > 0
        else 0.0
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    expected_accepted = TOTAL_INPUTS // 2
    expected_rejected = TOTAL_INPUTS - expected_accepted

    passed = True

    if accepted != expected_accepted:
        passed = False

    if rejected != expected_rejected:
        passed = False

    if unexpected != 0:
        passed = False

    # ========================================================
    # RESULTS
    # ========================================================

    print()
    print("=" * 60)
    print("SANITIZER BENCHMARK RESULTS")
    print("=" * 60)

    print(f"Inputs processed       : {TOTAL_INPUTS}")
    print(f"Accepted inputs        : {accepted}")
    print(f"Rejected inputs        : {rejected}")
    print(f"Unexpected results     : {unexpected}")
    print(f"Acceptance rate        : {accepted_percentage:.2f}%")
    print(f"Rejection rate         : {rejected_percentage:.2f}%")
    print(f"Total benchmark time   : {duration:.4f} seconds")
    print(f"Sanitization rate      : {rate:.2f} inputs/sec")

    print("=" * 60)

    if passed:
        print("[PASS] Sanitizer benchmark")
    else:
        print("[FAIL] Sanitizer benchmark")

    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_benchmark()