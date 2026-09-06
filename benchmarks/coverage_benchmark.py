import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.executor import Executor
from src.mutator import Mutator
from src.coverage_guided import CoverageGuidedScheduler


def run_coverage_benchmark():

    target = PROJECT_ROOT / "src" / "target.py"

    executor = Executor(
        target,
        timeout=1.0
    )

    mutator = Mutator()
    scheduler = CoverageGuidedScheduler()

    seed = b"SEED"

    corpus = [seed]
    total_coverage = set()

    checkpoints = [20, 40, 60, 80, 100]
    results = []

    start = time.perf_counter()

    for iteration in range(1, 101):

        if not scheduler.is_empty():
            current_input = scheduler.select()
        else:
            current_input = corpus[0]

        mutated = mutator.mutate(current_input)

        result = executor.run(mutated)

        coverage = (
            getattr(result, "coverage", set())
            or set()
        )

        new_coverage = (
            set(coverage) - total_coverage
        )

        if new_coverage:

            total_coverage.update(
                new_coverage
            )

            corpus.append(mutated)

            scheduler.add(
                mutated,
                coverage
            )

        if iteration in checkpoints:

            elapsed = (
                time.perf_counter() - start
            )

            results.append(
                (
                    iteration,
                    len(total_coverage),
                    len(corpus),
                    scheduler.size(),
                    elapsed
                )
            )

    print()
    print("=" * 65)
    print("COVERAGE BENCHMARK")
    print("=" * 65)

    print(
        f"{'Iteration':<12}"
        f"{'Coverage':<12}"
        f"{'Corpus':<12}"
        f"{'Scheduler':<12}"
        f"{'Time (s)':<12}"
    )

    print("-" * 65)

    for (
        iteration,
        coverage,
        corpus_size,
        scheduler_size,
        elapsed
    ) in results:

        print(
            f"{iteration:<12}"
            f"{coverage:<12}"
            f"{corpus_size:<12}"
            f"{scheduler_size:<12}"
            f"{elapsed:<12.2f}"
        )

    print("=" * 65)


if __name__ == "__main__":

    run_coverage_benchmark()