from __future__ import annotations

import sys
import shutil
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

from src.crash_database import CrashDatabase


# ============================================================
# CONFIGURATION
# ============================================================

BENCHMARK_DIRECTORY = PROJECT_ROOT / "benchmark_crashes"

CRASH_COUNT = 100


# ============================================================
# CRASH DIRECTORY BENCHMARK
# ============================================================

def run_benchmark():

    print()
    print("=" * 60)
    print("CRASH DIRECTORY BENCHMARK")
    print("=" * 60)

    print(
        f"Crash inputs     : "
        f"{CRASH_COUNT}"
    )

    print(
        f"Directory        : "
        f"{BENCHMARK_DIRECTORY}"
    )

    # ========================================================
    # CLEAN PREVIOUS BENCHMARK DATA
    # ========================================================

    if BENCHMARK_DIRECTORY.exists():
        shutil.rmtree(
            BENCHMARK_DIRECTORY
        )

    BENCHMARK_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # CREATE CRASH DATABASE
    # ========================================================

    database = CrashDatabase(
        BENCHMARK_DIRECTORY
    )

    # ========================================================
    # GENERATE AND SAVE CRASHES
    # ========================================================

    start_time = time.perf_counter()

    unique_saved = 0
    duplicate_crashes = 0

    for i in range(CRASH_COUNT):

        signature = (
            f"RuntimeError: "
            f"Benchmark crash {i}"
        )

        input_data = (
            f"CRASH_{i}".encode()
        )

        metadata = {
            "crash_type": "RuntimeError",
            "message": (
                f"Benchmark crash {i}"
            ),
            "benchmark_id": i,
        }

        stored = database.add_crash(
            signature=signature,
            input_data=input_data,
            metadata=metadata,
        )

        if stored:
            unique_saved += 1
        else:
            duplicate_crashes += 1

    duration = (
        time.perf_counter()
        - start_time
    )

    # ========================================================
    # VERIFY GENERATED FILES
    # ========================================================

    binary_files = list(
        BENCHMARK_DIRECTORY.glob("*.bin")
    )

    hash_file = (
        BENCHMARK_DIRECTORY
        / "crash_hashes.txt"
    )

    metadata_files = [
        path
        for path in BENCHMARK_DIRECTORY.glob(
            "crash_*.txt"
        )
        if path != hash_file
    ]

    # ========================================================
    # RESULTS
    # ========================================================

    print()
    print("=" * 60)
    print("CRASH DIRECTORY RESULTS")
    print("=" * 60)

    print(
        f"Crashes requested     : "
        f"{CRASH_COUNT}"
    )

    print(
        f"Unique crashes saved  : "
        f"{unique_saved}"
    )

    print(
        f"Duplicate crashes     : "
        f"{duplicate_crashes}"
    )

    print(
        f"Database count        : "
        f"{database.count()}"
    )

    print(
        f"Binary files          : "
        f"{len(binary_files)}"
    )

    print(
        f"Metadata files        : "
        f"{len(metadata_files)}"
    )

    print(
        f"Hash database exists  : "
        f"{hash_file.exists()}"
    )

    print(
        f"Save duration         : "
        f"{duration:.4f} seconds"
    )

    if duration > 0:

        print(
            f"Save rate             : "
            f"{CRASH_COUNT / duration:.2f} "
            f"crashes/sec"
        )

    else:

        print(
            "Save rate             : N/A"
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    passed = (
        unique_saved == CRASH_COUNT
        and duplicate_crashes == 0
        and database.count() == CRASH_COUNT
        and len(binary_files) == CRASH_COUNT
        and len(metadata_files) == CRASH_COUNT
        and hash_file.exists()
    )

    print()

    if passed:

        print(
            "[PASS] Crash directory benchmark"
        )

    else:

        print(
            "[FAIL] Crash directory benchmark"
        )

    print("=" * 60)

    return passed


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_benchmark()