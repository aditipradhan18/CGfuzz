import argparse

from .executor import Executor
from .fuzzer import Fuzzer


def build_parser() -> argparse.ArgumentParser:
    """
    Build the AstraFuzz command-line argument parser.
    """

    parser = argparse.ArgumentParser(
        prog="astrafuzz",
        description=(
            "AstraFuzz - coverage-guided mutation fuzzer"
        )
    )

    # ---------------------------------------------------------
    # TARGET
    # ---------------------------------------------------------

    parser.add_argument(
        "--target",
        required=True,
        help=(
            "Path to the Python target program "
            "to fuzz."
        )
    )

    # ---------------------------------------------------------
    # SEED
    # ---------------------------------------------------------

    parser.add_argument(
        "--seed",
        default="CRASH",
        help=(
            "Initial seed input as a string. "
            "Default: CRASH"
        )
    )

    # ---------------------------------------------------------
    # ITERATIONS
    # ---------------------------------------------------------

    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help=(
            "Number of fuzzing iterations. "
            "Default: 1000"
        )
    )

    # ---------------------------------------------------------
    # TIMEOUT
    # ---------------------------------------------------------

    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help=(
            "Target execution timeout in seconds. "
            "Default: 1.0"
        )
    )

    # ---------------------------------------------------------
    # MAX INPUT SIZE
    # ---------------------------------------------------------

    parser.add_argument(
        "--max-input-size",
        type=int,
        default=4096,
        help=(
            "Maximum accepted fuzzing input size "
            "in bytes. Default: 4096"
        )
    )

    # ---------------------------------------------------------
    # REPRODUCTION ATTEMPTS
    # ---------------------------------------------------------

    parser.add_argument(
        "--reproduction-attempts",
        type=int,
        default=3,
        help=(
            "Number of attempts used to reproduce "
            "a crash. Default: 3"
        )
    )

    return parser


def validate_arguments(args):
    """
    Validate command-line configuration.
    """

    if args.iterations < 1:
        raise ValueError(
            "iterations must be greater than 0"
        )

    if args.timeout <= 0:
        raise ValueError(
            "timeout must be greater than 0"
        )

    if args.max_input_size < 1:
        raise ValueError(
            "max-input-size must be greater than 0"
        )

    if args.reproduction_attempts < 1:
        raise ValueError(
            "reproduction-attempts must be greater than 0"
        )


def main():
    """
    AstraFuzz command-line entry point.
    """

    parser = build_parser()

    args = parser.parse_args()

    try:
        validate_arguments(args)

    except ValueError as error:

        parser.error(str(error))

    # ---------------------------------------------------------
    # DISPLAY CONFIGURATION
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("ASTRAFUZZ CONFIGURATION")
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
        f"Max input size      : "
        f"{args.max_input_size} bytes"
    )

    print(
        f"Reproduction runs   : "
        f"{args.reproduction_attempts}"
    )

    print("=" * 60)

    # ---------------------------------------------------------
    # BUILD EXECUTOR
    # ---------------------------------------------------------

    executor = Executor(
        target=args.target,
        timeout=args.timeout
    )

    # ---------------------------------------------------------
    # BUILD FUZZER
    # ---------------------------------------------------------

    fuzzer = Fuzzer(
        executor=executor,
        iterations=args.iterations,
        max_input_size=args.max_input_size,
        reproduction_attempts=args.reproduction_attempts
    )

    # ---------------------------------------------------------
    # RUN CAMPAIGN
    # ---------------------------------------------------------

    fuzzer.run(
        args.seed.encode()
    )


if __name__ == "__main__":
    main()