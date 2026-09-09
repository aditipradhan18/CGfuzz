import sys
import time
from pathlib import Path

# =============================================================
# PROJECT ROOT
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================
# IMPORT CGFUZZ
# =============================================================

from src.executor import Executor
from src.fuzzer import Fuzzer


# =============================================================
# BENCHMARK
# =============================================================

def run_cgfuzz():
    target = PROJECT_ROOT / "src" / "target.py"
    seed = b"CRASH"
    iterations = 100

    # ---------------------------------------------------------
    # Create the target executor
    # ---------------------------------------------------------

    executor = Executor(
        target,
        timeout=1.0
    )

    # ---------------------------------------------------------
    # Create CGFuzz
    # ---------------------------------------------------------

    fuzzer = Fuzzer(
        executor=executor,
        iterations=iterations,
        max_input_size=4096,
        reproduction_attempts=3,
        workers=1
    )

    # ---------------------------------------------------------
    # Run the campaign
    # ---------------------------------------------------------

    start = time.perf_counter()

    fuzzer.run(seed)

    duration = time.perf_counter() - start

    # ---------------------------------------------------------
    # Extract authoritative Fuzzer statistics
    # ---------------------------------------------------------

    stats = fuzzer.get_statistics()

    executions = stats.get("executions", 0)
    crashes = stats.get("crashes", 0)
    timeouts = stats.get("timeouts", 0)
    rejected = stats.get("rejected_inputs", 0)

    coverage = stats.get("coverage_lines", 0)
    coverage_finds = stats.get("coverage_discoveries", 0)
    bitmap_coverage = stats.get("bitmap_coverage", 0)

    corpus_size = stats.get("corpus_size", 0)
    scheduler_entries = stats.get("scheduler_entries", 0)

    reproduced = stats.get("reproduced_crashes", 0)

    # ---------------------------------------------------------
    # Derived metrics
    # ---------------------------------------------------------

    execution_rate = (
        executions / duration
        if duration > 0
        else 0.0
    )

    avg_exec_time = (
        (duration / executions) * 1000
        if executions > 0
        else 0.0
    )

    crash_rate = (
        (crashes / executions) * 100
        if executions > 0
        else 0.0
    )

    # ---------------------------------------------------------
    # Clean benchmark summary
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("CGFUZZ BENCHMARK RESULTS")
    print("=" * 60)

    print(f"Seed              : {seed!r}")
    print(f"Iterations        : {iterations}")
    print(f"Executions        : {executions}")
    print(f"Duration          : {duration:.2f} seconds")
    print(f"Execution rate    : {execution_rate:.2f} exec/sec")
    print(f"Avg exec time     : {avg_exec_time:.2f} ms")

    print()

    print(f"Crashes found     : {crashes}")
    print(f"Crash rate        : {crash_rate:.2f}%")
    print(f"Reproduced        : {reproduced}")

    print()

    print(f"Timeouts          : {timeouts}")
    print(f"Rejected inputs   : {rejected}")

    print()

    print(f"Coverage lines    : {coverage}")
    print(f"Coverage finds    : {coverage_finds}")
    print(f"Bitmap coverage   : {bitmap_coverage}")
    print(f"Corpus size       : {corpus_size}")
    print(f"Scheduler entries : {scheduler_entries}")

    print("=" * 60)


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":
    run_cgfuzz()