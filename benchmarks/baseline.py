import random
import time
import sys
from pathlib import Path


# =============================================================
# PROJECT PATH
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================
# CGFUZZ COMPONENTS
# =============================================================

from src.executor import Executor, ExecutionStatus
from src.mutator import Mutator


# =============================================================
# BASELINE FUZZER
# =============================================================

def run_baseline(
    seed: bytes = b"CRASH",
    iterations: int = 1000,
    timeout: float = 1.0
):
    """
    Random-mutation baseline used for comparison with CGFuzz.

    The baseline uses:
        - the same target
        - the same Executor
        - the same Mutator

    The only major difference is input selection:

        Baseline -> random corpus selection
        CGFuzz  -> coverage-guided selection
    """

    # =========================================================
    # TARGET
    # =========================================================

    target = PROJECT_ROOT / "src" / "target.py"

    executor = Executor(
        target,
        timeout=timeout
    )

    mutator = Mutator()

    # =========================================================
    # CORPUS
    # =========================================================

    corpus = [seed]

    # =========================================================
    # STATISTICS
    # =========================================================

    executions = 0
    crashes = 0
    timeouts = 0

    total_execution_time = 0.0

    coverage = set()

    # =========================================================
    # START TIMER
    # =========================================================

    start_time = time.perf_counter()

    print()
    print("=" * 60)
    print("BASELINE FUZZING BENCHMARK")
    print("=" * 60)
    print(f"Seed              : {seed!r}")
    print(f"Iterations        : {iterations}")
    print(f"Timeout            : {timeout} seconds")
    print("=" * 60)
    print()

    # =========================================================
    # INITIAL SEED
    # =========================================================

    result = executor.run(seed)

    executions += 1
    total_execution_time += result.duration

    result_coverage = (
        getattr(result, "coverage", set())
        or set()
    )

    coverage.update(result_coverage)

    if result.status == ExecutionStatus.CRASH:
        crashes += 1

    elif result.status == ExecutionStatus.TIMEOUT:
        timeouts += 1

    # =========================================================
    # FUZZING LOOP
    # =========================================================

    for iteration in range(1, iterations + 1):

        # -----------------------------------------------------
        # RANDOM SELECTION
        # -----------------------------------------------------

        current_input = random.choice(corpus)

        # -----------------------------------------------------
        # MUTATION
        # -----------------------------------------------------

        mutated_input = mutator.mutate(
            current_input
        )

        # -----------------------------------------------------
        # EXECUTION
        # -----------------------------------------------------

        result = executor.run(
            mutated_input
        )

        executions += 1

        total_execution_time += result.duration

        # -----------------------------------------------------
        # COVERAGE
        # -----------------------------------------------------

        result_coverage = (
            getattr(result, "coverage", set())
            or set()
        )

        coverage.update(result_coverage)

        # -----------------------------------------------------
        # RESULT
        # -----------------------------------------------------

        if result.status == ExecutionStatus.CRASH:

            crashes += 1

        elif result.status == ExecutionStatus.TIMEOUT:

            timeouts += 1

        # -----------------------------------------------------
        # BASELINE CORPUS
        # -----------------------------------------------------

        corpus.append(
            mutated_input
        )

        # -----------------------------------------------------
        # PROGRESS
        # -----------------------------------------------------

        if iteration % 100 == 0:

            elapsed = (
                time.perf_counter()
                - start_time
            )

            rate = (
                executions / elapsed
                if elapsed > 0
                else 0.0
            )

            print(
                f"[Progress] "
                f"{iteration}/{iterations} "
                f"| executions={executions} "
                f"| crashes={crashes} "
                f"| coverage={len(coverage)} "
                f"| rate={rate:.2f} exec/sec"
            )

    # =========================================================
    # STOP TIMER
    # =========================================================

    end_time = time.perf_counter()

    duration = (
        end_time - start_time
    )

    # =========================================================
    # DERIVED METRICS
    # =========================================================

    if duration > 0:

        executions_per_second = (
            executions / duration
        )

    else:

        executions_per_second = 0.0

    if executions > 0:

        average_execution_time = (
            total_execution_time
            / executions
        )

    else:

        average_execution_time = 0.0

    # =========================================================
    # FINAL RESULTS
    # =========================================================

    print()
    print("=" * 60)
    print("BASELINE RESULTS")
    print("=" * 60)

    print(
        f"Seed              : {seed!r}"
    )

    print(
        f"Iterations        : {iterations}"
    )

    print(
        f"Executions        : {executions}"
    )

    print(
        f"Duration          : {duration:.2f} seconds"
    )

    print(
        f"Execution rate    : "
        f"{executions_per_second:.2f} exec/sec"
    )

    print(
        f"Avg exec time     : "
        f"{average_execution_time * 1000:.2f} ms"
    )

    print()

    print(
        f"Crashes           : {crashes}"
    )

    print(
        f"Timeouts          : {timeouts}"
    )

    print(
        f"Coverage lines    : {len(coverage)}"
    )

    print(
        f"Corpus size       : {len(corpus)}"
    )

    print("=" * 60)


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":

    run_baseline(
        seed=b"CRASH",
        iterations=100,
        timeout=1.0
    )