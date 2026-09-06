from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from src.executor import Executor
from src.fuzzer import Fuzzer


# =============================================================
# CONFIGURATION
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TARGET = PROJECT_ROOT / "src" / "target.py"

SEED = b"CRASH"

ITERATIONS = 30
TIMEOUT = 1.0
MAX_INPUT_SIZE = 4096
REPRODUCTION_RUNS = 3

FINAL_DEMO_DIRECTORY = PROJECT_ROOT / "benchmark_final_demo"

CRASH_DIRECTORY = FINAL_DEMO_DIRECTORY / "crashes"
CORPUS_DIRECTORY = FINAL_DEMO_DIRECTORY / "corpus"


# =============================================================
# DIRECTORY MANAGEMENT
# =============================================================

def prepare_demo_directory() -> None:
    """
    Prepare a clean directory for the final demonstration.
    """

    if FINAL_DEMO_DIRECTORY.exists():
        shutil.rmtree(FINAL_DEMO_DIRECTORY)

    FINAL_DEMO_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    CRASH_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    CORPUS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )


# =============================================================
# ARTIFACT COUNTING
# =============================================================

def count_files(
    directory: Path,
    suffix: str | None = None
) -> int:
    """
    Count files in a directory.

    If suffix is supplied, only files with that suffix
    are counted.
    """

    if not directory.exists():
        return 0

    files = [
        path
        for path in directory.iterdir()
        if path.is_file()
    ]

    if suffix is not None:
        files = [
            path
            for path in files
            if path.suffix.lower() == suffix.lower()
        ]

    return len(files)


# =============================================================
# CORPUS ARTIFACTS
# =============================================================

def create_corpus_artifacts(
    fuzzer: Fuzzer
) -> int:
    """
    Persist the in-memory corpus into the final demo directory.
    """

    if not hasattr(fuzzer, "corpus"):
        return 0

    corpus = fuzzer.corpus

    entries = []

    if hasattr(corpus, "entries"):
        entries = corpus.entries

    elif hasattr(corpus, "_entries"):
        entries = corpus._entries

    elif hasattr(corpus, "data"):
        entries = corpus.data

    elif hasattr(corpus, "_data"):
        entries = corpus._data

    normalized = []

    if isinstance(entries, dict):
        normalized = list(entries.values())

    elif isinstance(entries, (list, tuple, set)):
        normalized = list(entries)

    extracted = []

    for entry in normalized:

        data = None

        if isinstance(entry, bytes):
            data = entry

        elif isinstance(entry, bytearray):
            data = bytes(entry)

        elif hasattr(entry, "data"):

            value = entry.data

            if isinstance(value, bytes):
                data = value

            elif isinstance(value, bytearray):
                data = bytes(value)

        elif isinstance(entry, tuple) and entry:

            first = entry[0]

            if isinstance(first, bytes):
                data = first

            elif isinstance(first, bytearray):
                data = bytes(first)

        if data is not None:
            extracted.append(data)

    unique_inputs = []

    seen = set()

    for data in extracted:

        if data in seen:
            continue

        seen.add(data)
        unique_inputs.append(data)

    for index, data in enumerate(
        unique_inputs,
        start=1
    ):

        output_file = (
            CORPUS_DIRECTORY /
            f"corpus_{index:04d}.bin"
        )

        try:
            output_file.write_bytes(data)

        except OSError:
            continue

    return count_files(
        CORPUS_DIRECTORY,
        ".bin"
    )


# =============================================================
# FALLBACK CORPUS ARTIFACT
# =============================================================

def ensure_corpus_artifact(
    fuzzer: Fuzzer
) -> int:
    """
    Ensure at least one corpus artifact exists when the
    fuzzer reports a populated corpus.
    """

    existing = count_files(
        CORPUS_DIRECTORY,
        ".bin"
    )

    if existing > 0:
        return existing

    try:
        corpus_size = fuzzer.corpus.size()

    except Exception:
        corpus_size = 0

    if corpus_size <= 0:
        return 0

    fallback = (
        CORPUS_DIRECTORY /
        "corpus_seed.bin"
    )

    try:
        fallback.write_bytes(SEED)

    except OSError:
        return existing

    return count_files(
        CORPUS_DIRECTORY,
        ".bin"
    )


# =============================================================
# HEADER
# =============================================================

def print_header() -> None:

    print()
    print("=" * 60)
    print("CGFUZZ END-TO-END FINAL DEMO")
    print("=" * 60)

    print(
        f"Target              : {TARGET}"
    )

    print(
        f"Seed                : {SEED!r}"
    )

    print(
        f"Iterations          : {ITERATIONS}"
    )

    print(
        f"Timeout             : {TIMEOUT} seconds"
    )

    print(
        f"Maximum input size  : "
        f"{MAX_INPUT_SIZE} bytes"
    )

    print(
        f"Reproduction runs   : "
        f"{REPRODUCTION_RUNS}"
    )

    print("=" * 60)


# =============================================================
# PIPELINE
# =============================================================

def print_pipeline() -> None:

    print()
    print(
        "[*] Running complete CGFuzz pipeline..."
    )

    print()

    print(
        "    Sanitizer -> Executor -> Coverage -> "
        "Scheduler -> Mutation -> Crash Analysis -> "
        "Minimization -> Reproduction -> Database"
    )

    print()


# =============================================================
# FINAL RESULTS
# =============================================================

def print_final_results(
    total_time: float,
    statistics: dict,
    crash_binary_files: int,
    crash_report_files: int,
    corpus_files: int
) -> None:

    print()
    print("=" * 60)
    print("END-TO-END FINAL RESULTS")
    print("=" * 60)

    print(
        f"Total benchmark time : "
        f"{total_time:.4f} seconds"
    )

    print(
        f"Executions           : "
        f"{statistics.get('executions', 0)}"
    )

    print(
        f"Execution rate       : "
        f"{statistics.get('executions_per_second', 0.0):.2f} "
        f"exec/sec"
    )

    print(
        f"Crashes found        : "
        f"{statistics.get('crashes', 0)}"
    )

    print(
        f"Reproduced crashes   : "
        f"{statistics.get('reproduced_crashes', 0)}"
    )

    print(
        f"Timeouts             : "
        f"{statistics.get('timeouts', 0)}"
    )

    print(
        f"Rejected inputs      : "
        f"{statistics.get('rejected_inputs', 0)}"
    )

    print(
        f"Coverage lines       : "
        f"{statistics.get('coverage_lines', 0)}"
    )

    print(
        f"Coverage discoveries : "
        f"{statistics.get('coverage_discoveries', 0)}"
    )

    print(
        f"Corpus size          : "
        f"{statistics.get('corpus_size', 0)}"
    )

    print(
        f"Scheduler entries    : "
        f"{statistics.get('scheduler_entries', 0)}"
    )

    print(
        f"Crash binary files   : "
        f"{crash_binary_files}"
    )

    print(
        f"Crash report files   : "
        f"{crash_report_files}"
    )

    print(
        f"Corpus files         : "
        f"{corpus_files}"
    )

    print()
    print("=" * 60)


# =============================================================
# PIPELINE VALIDATION
# =============================================================

def validate_pipeline(
    statistics: dict,
    crash_binary_files: int,
    crash_report_files: int,
    corpus_files: int
) -> bool:

    print()
    print("=" * 60)
    print("PIPELINE VALIDATION")
    print("=" * 60)

    checks = []

    # ---------------------------------------------------------
    # Executions
    # ---------------------------------------------------------

    checks.append(
        (
            "Executions performed",
            statistics.get("executions", 0) > 0
        )
    )

    # ---------------------------------------------------------
    # Coverage
    # ---------------------------------------------------------

    checks.append(
        (
            "Coverage collected",
            statistics.get("coverage_lines", 0) > 0
        )
    )

    # ---------------------------------------------------------
    # Corpus
    # ---------------------------------------------------------

    checks.append(
        (
            "Corpus populated",
            statistics.get("corpus_size", 0) > 0
        )
    )

    # ---------------------------------------------------------
    # Scheduler
    # ---------------------------------------------------------

    checks.append(
        (
            "Scheduler populated",
            statistics.get("scheduler_entries", 0) > 0
        )
    )

    # ---------------------------------------------------------
    # Crash discovery
    # ---------------------------------------------------------

    checks.append(
        (
            "Seed crash discovered",
            statistics.get("crashes", 0) > 0
        )
    )

    # ---------------------------------------------------------
    # Crash artifacts
    # ---------------------------------------------------------

    checks.append(
        (
            "Crash artifacts saved",
            crash_binary_files > 0
        )
    )

    # ---------------------------------------------------------
    # Crash reports
    # ---------------------------------------------------------

    checks.append(
        (
            "Crash reports saved",
            crash_report_files > 0
        )
    )

    # ---------------------------------------------------------
    # Reproduction
    # ---------------------------------------------------------

    checks.append(
        (
            "Crash reproduction completed",
            statistics.get("reproduced_crashes", 0) > 0
        )
    )

    # ---------------------------------------------------------
    # Rejected inputs
    # ---------------------------------------------------------

    checks.append(
        (
            "No unexpected rejected inputs",
            statistics.get("rejected_inputs", 0) == 0
        )
    )

    # ---------------------------------------------------------
    # Print checks
    # ---------------------------------------------------------

    all_passed = True

    for description, passed in checks:

        if passed:

            print(
                f"[PASS] {description}"
            )

        else:

            print(
                f"[FAIL] {description}"
            )

            all_passed = False

    print("=" * 60)

    if all_passed:

        print(
            "[PASS] CGFuzz end-to-end final demo"
        )

    else:

        print(
            "[FAIL] CGFuzz end-to-end final demo"
        )

    print("=" * 60)

    return all_passed


# =============================================================
# MAIN BENCHMARK
# =============================================================

def run_benchmark() -> None:

    print_header()

    # ---------------------------------------------------------
    # Validate target
    # ---------------------------------------------------------

    if not TARGET.exists():

        print()

        print(
            f"[FAIL] Target does not exist: {TARGET}"
        )

        return

    # ---------------------------------------------------------
    # Prepare isolated directory
    # ---------------------------------------------------------

    prepare_demo_directory()

    print_pipeline()

    # ---------------------------------------------------------
    # Create executor
    # ---------------------------------------------------------

    executor = Executor(
        target=str(TARGET),
        timeout=TIMEOUT
    )

    # ---------------------------------------------------------
    # Save current directory
    # ---------------------------------------------------------

    previous_directory = Path.cwd()

    fuzzer = None

    benchmark_start = time.perf_counter()

    try:

        # -----------------------------------------------------
        # Run Fuzzer from isolated demo directory.
        #
        # Fuzzer internally creates:
        #
        #     crashes/
        #
        # -----------------------------------------------------

        os.chdir(
            FINAL_DEMO_DIRECTORY
        )

        fuzzer = Fuzzer(
            executor=executor,
            iterations=ITERATIONS,
            max_input_size=MAX_INPUT_SIZE,
            reproduction_attempts=REPRODUCTION_RUNS,
        )

        fuzzer.run(
            SEED
        )

    finally:

        os.chdir(
            previous_directory
        )

    benchmark_end = time.perf_counter()

    total_time = (
        benchmark_end -
        benchmark_start
    )

    # ---------------------------------------------------------
    # Safety check
    # ---------------------------------------------------------

    if fuzzer is None:

        print()

        print(
            "[FAIL] Fuzzer could not be initialized."
        )

        return

    # ---------------------------------------------------------
    # Get actual Fuzzer statistics
    # ---------------------------------------------------------

    statistics = (
        fuzzer.get_statistics()
    )

    # ---------------------------------------------------------
    # Persist corpus artifacts
    # ---------------------------------------------------------

    create_corpus_artifacts(
        fuzzer
    )

    corpus_files = (
        ensure_corpus_artifact(
            fuzzer
        )
    )

    # ---------------------------------------------------------
    # Count crash artifacts
    # ---------------------------------------------------------

    crash_binary_files = count_files(
        CRASH_DIRECTORY,
        ".bin"
    )

    # ---------------------------------------------------------
    # IMPORTANT:
    #
    # The CrashDatabase also creates .txt metadata files.
    # The actual crash reports are named:
    #
    #     crash_<hash>.txt
    #
    # Count only those files.
    # ---------------------------------------------------------

    crash_report_files = len(
        list(
            CRASH_DIRECTORY.glob(
                "crash_*.txt"
            )
        )
    )

    # ---------------------------------------------------------
    # Final results
    # ---------------------------------------------------------

    print_final_results(
        total_time=total_time,
        statistics=statistics,
        crash_binary_files=crash_binary_files,
        crash_report_files=crash_report_files,
        corpus_files=corpus_files
    )

    # ---------------------------------------------------------
    # Validate
    # ---------------------------------------------------------

    passed = validate_pipeline(
        statistics=statistics,
        crash_binary_files=crash_binary_files,
        crash_report_files=crash_report_files,
        corpus_files=corpus_files
    )

    print()

    print(
        f"Demo artifacts: "
        f"{FINAL_DEMO_DIRECTORY}"
    )

    print()

    if not passed:
        raise SystemExit(1)


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":
    run_benchmark()