"""
Command-line interface for CGFuzz.
"""

from __future__ import annotations

import argparse

from .executor import Executor
from .fuzzer import Fuzzer


# ============================================================
# ARGUMENT PARSER
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """
    Build the CGFuzz command-line argument parser.
    """

    parser = argparse.ArgumentParser(
        description="Coverage-guided mutation fuzzer"
    )

    parser.add_argument(
        "--target",
        required=True,
        help="Target program to fuzz"
    )

    parser.add_argument(
        "--seed",
        default="CRASH",
        help="Initial fuzzing seed (default: CRASH)"
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Number of mutation iterations (default: 1000)"
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="Target execution timeout in seconds (default: 1.0)"
    )

    parser.add_argument(
        "--max-input-size",
        type=int,
        default=4096,
        help="Maximum accepted input size in bytes (default: 4096)"
    )

    parser.add_argument(
        "--reproduction-attempts",
        type=int,
        default=3,
        help="Number of crash reproduction attempts (default: 3)"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "Number of distributed fuzzing workers. "
            "Default: 1"
        )
    )

    return parser


# ============================================================
# ARGUMENT VALIDATION
# ============================================================

def validate_arguments(
    args: argparse.Namespace
) -> None:
    """
    Validate command-line arguments.
    """

    if args.iterations < 1:
        raise ValueError(
            "iterations must be at least 1"
        )

    if args.timeout <= 0:
        raise ValueError(
            "timeout must be greater than 0"
        )

    if args.max_input_size < 1:
        raise ValueError(
            "max_input_size must be greater than 0"
        )

    if args.reproduction_attempts < 1:
        raise ValueError(
            "reproduction_attempts must be greater than 0"
        )

    if args.workers < 1:
        raise ValueError(
            "workers must be greater than 0"
        )


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    """
    Main command-line entry point.
    """

    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_arguments(args)

    except ValueError as exc:
        parser.error(str(exc))

    print()
    print("=" * 60)
    print("CGFUZZ - COVERAGE-GUIDED MUTATION FUZZER")
    print("=" * 60)

    print(
        f"Target              : {args.target}"
    )

    print(
        f"Seed                : {args.seed!r}"
    )

    print(
        f"Iterations          : {args.iterations}"
    )

    print(
        f"Timeout             : {args.timeout} seconds"
    )

    print(
        f"Maximum input size  : {args.max_input_size} bytes"
    )

    print(
        f"Reproduction runs   : {args.reproduction_attempts}"
    )

    print(
        f"Workers             : {args.workers}"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # CREATE EXECUTOR
    # --------------------------------------------------------

    executor = Executor(
        target=args.target,
        timeout=args.timeout
    )

    # --------------------------------------------------------
    # CREATE FUZZER
    # --------------------------------------------------------

    fuzzer = Fuzzer(
        executor=executor,
        iterations=args.iterations,
        max_input_size=args.max_input_size,
        reproduction_attempts=args.reproduction_attempts,
        workers=args.workers
    )

    # --------------------------------------------------------
    # RUN CAMPAIGN
    # --------------------------------------------------------

    try:
        statistics = fuzzer.run(
            args.seed.encode("utf-8")
        )

    finally:
        executor.close()

    # --------------------------------------------------------
    # FINAL CLI SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("CLI CAMPAIGN RESULTS")
    print("=" * 60)

    print(
        f"Campaign duration : "
        f"{statistics['campaign_duration']:.2f} seconds"
    )

    print(
        f"Executions        : "
        f"{statistics['executions']}"
    )

    print(
        f"Execution rate    : "
        f"{statistics['executions_per_second']:.2f} exec/sec"
    )

    print(
        f"Avg exec time     : "
        f"{statistics['average_execution_time'] * 1000:.2f} ms"
    )

    print(
        f"Workers           : "
        f"{statistics['workers']}"
    )

    print()

    print(
        f"Crashes found     : "
        f"{statistics['crashes']}"
    )

    print(
        f"Crash rate        : "
        f"{statistics['crash_rate']:.2f}%"
    )

    print(
        f"Unique crashes    : "
        f"{statistics['unique_crashes']}"
    )

    print(
        f"Unique crash rate : "
        f"{statistics['unique_crash_rate']:.2f}%"
    )

    print(
        f"Reproduced        : "
        f"{statistics['reproduced_crashes']}"
    )

    print()

    print(
        f"Timeouts          : "
        f"{statistics['timeouts']}"
    )

    print(
        f"Rejected inputs   : "
        f"{statistics['rejected_inputs']}"
    )

    print()

    print(
        f"Coverage lines    : "
        f"{statistics['coverage_lines']}"
    )

    print(
        f"Coverage finds    : "
        f"{statistics['coverage_discoveries']}"
    )

    print(
        f"Bitmap coverage   : "
        f"{statistics['bitmap_coverage']}"
    )

    print(
        f"Corpus size       : "
        f"{statistics['corpus_size']}"
    )

    print(
        f"Scheduler entries : "
        f"{statistics['scheduler_entries']}"
    )

    print("=" * 60)

    return 0


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":
    raise SystemExit(main())