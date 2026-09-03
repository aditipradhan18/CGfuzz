import argparse
import hashlib
from pathlib import Path

from src.executor import Executor, ExecutionStatus
from src.mutator import Mutator
from src.corpus import Corpus
from src.crash_minimizer import CrashMinimizer
from src.crash_classifier import CrashClassifier


class Fuzzer:
    """
    Coverage-guided mutation fuzzer.

    Pipeline:

        Seed
          ↓
        Execute seed
          ↓
        Coverage
          ↓
        Corpus
          ↓
        Select input
          ↓
        Mutate
          ↓
        Execute
          ↓
        Coverage / Crash
          ↓
        Corpus / Crash storage
    """

    def __init__(
        self,
        executor: Executor,
        iterations: int = 1000
    ):
        self.executor = executor
        self.mutator = Mutator()
        self.minimizer = CrashMinimizer(executor)
        self.crash_classifier = CrashClassifier()

        self.iterations = iterations

        # -----------------------------------------------------
        # CORPUS
        # -----------------------------------------------------

        self.corpus = Corpus()

        # -----------------------------------------------------
        # GLOBAL COVERAGE
        # -----------------------------------------------------

        self.total_coverage = set()

        # -----------------------------------------------------
        # RUNTIME STATISTICS
        # -----------------------------------------------------

        self.executions = 0
        self.crashes = 0
        self.timeouts = 0

        # -----------------------------------------------------
        # CRASH DEDUPLICATION
        # -----------------------------------------------------

        self.saved_crashes = set()

        # -----------------------------------------------------
        # CRASH DIRECTORY
        # -----------------------------------------------------

        self.crash_directory = Path("crashes")

        self.crash_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        self.hash_file = (
            self.crash_directory /
            "crash_hashes.txt"
        )

    # =========================================================
    # HASHING
    # =========================================================

    def calculate_hash(
        self,
        data: bytes
    ) -> str:
        """
        Generate SHA-256 fingerprint
        for an input.
        """

        return hashlib.sha256(
            data
        ).hexdigest()

    # =========================================================
    # LOAD PREVIOUS CRASH HASHES
    # =========================================================

    def load_saved_hashes(self):
        """
        Load previously saved crash fingerprints.
        """

        if not self.hash_file.exists():
            return

        try:
            with self.hash_file.open(
                "r",
                encoding="utf-8"
            ) as file:

                for line in file:

                    value = line.strip()

                    if value:
                        self.saved_crashes.add(
                            value
                        )

        except OSError as error:

            print(
                f"[!] Could not load crash hashes: {error}"
            )

    # =========================================================
    # SAVE CRASH HASH
    # =========================================================

    def store_crash_hash(
        self,
        crash_hash: str
    ):
        """
        Persist crash fingerprint.
        """

        try:

            with self.hash_file.open(
                "a",
                encoding="utf-8"
            ) as file:

                file.write(
                    crash_hash + "\n"
                )

        except OSError as error:

            print(
                f"[!] Could not save crash hash: {error}"
            )

    # =========================================================
    # CORPUS
    # =========================================================

    def add_to_corpus(
        self,
        data: bytes,
        coverage: set
    ) -> bool:
        """
        Add an input when it discovers
        new coverage.
        """

        coverage = set(coverage)

        new_coverage = (
            coverage -
            self.total_coverage
        )

        if not new_coverage:
            return False

        self.total_coverage.update(
            new_coverage
        )

        self.corpus.add(
            data,
            coverage
        )

        return True

    # =========================================================
    # SAVE CRASH
    # =========================================================

    def save_crash(
        self,
        crashing_input: bytes
    ) -> bool:
        """
        Minimize, hash and save a unique crash.
        """

        print()
        print("=" * 55)
        print("CRASH DETECTED")
        print("=" * 55)

        print(
            f"Original input : {crashing_input!r}"
        )

        print(
            f"Original size  : "
            f"{len(crashing_input)} bytes"
        )

        # -----------------------------------------------------
        # MINIMIZE
        # -----------------------------------------------------

        minimized = self.minimizer.minimize(
            crashing_input
        )

        print(
            f"Minimized input: {minimized!r}"
        )

        print(
            f"Minimized size : "
            f"{len(minimized)} bytes"
        )

        # -----------------------------------------------------
        # HASH
        # -----------------------------------------------------

        crash_hash = self.calculate_hash(
            minimized
        )

        print(
            f"SHA-256        : {crash_hash}"
        )

        # -----------------------------------------------------
        # DEDUPLICATION
        # -----------------------------------------------------

        if crash_hash in self.saved_crashes:

            print(
                "Duplicate crash - already saved."
            )

            print("=" * 55)

            return False

        self.saved_crashes.add(
            crash_hash
        )

        self.store_crash_hash(
            crash_hash
        )

        # -----------------------------------------------------
        # CRASH NUMBER
        # -----------------------------------------------------

        crash_number = len(
            self.saved_crashes
        )

        crash_file = (
            self.crash_directory /
            f"crash_{crash_number}.bin"
        )

        report_file = (
            self.crash_directory /
            f"crash_{crash_number}.txt"
        )

        # -----------------------------------------------------
        # SAVE BINARY
        # -----------------------------------------------------

        try:

            crash_file.write_bytes(
                minimized
            )

        except OSError as error:

            print(
                f"[!] Could not save crash: {error}"
            )

            return False

        # -----------------------------------------------------
        # SAVE REPORT
        # -----------------------------------------------------

        report = (
            "FUZZER CRASH REPORT\n"
            "===================\n\n"
            f"SHA-256: {crash_hash}\n"
            f"Size: {len(minimized)} bytes\n"
            f"Input: {minimized!r}\n"
            f"Binary: {crash_file}\n"
        )

        try:

            report_file.write_text(
                report,
                encoding="utf-8"
            )

        except OSError as error:

            print(
                f"[!] Could not save crash report: {error}"
            )

        print()
        print("UNIQUE CRASH SAVED")

        print(
            f"Binary : {crash_file}"
        )

        print(
            f"Report : {report_file}"
        )

        print("=" * 55)

        return True

    # =========================================================
    # EXECUTE ONE INPUT
    # =========================================================

    def execute_input(
        self,
        data: bytes,
        iteration: int | str
    ) -> bool:
        """
        Execute one input.

        Returns True if execution produced
        a crash.
        """

        self.executions += 1

        result = self.executor.run(
            data
        )

        coverage = getattr(
            result,
            "coverage",
            set()
        )

        if coverage is None:
            coverage = set()

        coverage = set(coverage)

        # -----------------------------------------------------
        # TIMEOUT
        # -----------------------------------------------------

        if (
            result.status
            == ExecutionStatus.TIMEOUT
        ):

            self.timeouts += 1

            print(
                f"[{iteration}] "
                f"Input={data!r} "
                f"Status=TIMEOUT "
                f"Coverage={len(coverage)}"
            )

            return False

        # -----------------------------------------------------
        # CRASH
        # -----------------------------------------------------

        if (
            result.status
            == ExecutionStatus.CRASH
        ):

            self.crashes += 1

            classification = self.crash_classifier.classify(
                result
            )

            print(
                f"[{iteration}] "
                f"Input={data!r} "
                f"Status=CRASH "
                f"Type={classification.name} "
                f"Message={classification.message!r} "
                f"Coverage={len(coverage)}"
            )

            self.save_crash(
                data
            )

            self.add_to_corpus(
                data,
                coverage
            )

            return True

        # -----------------------------------------------------
        # NORMAL
        # -----------------------------------------------------

        print(
            f"[{iteration}] "
            f"Input={data!r} "
            f"Status=NORMAL "
            f"Coverage={len(coverage)}"
        )

        # -----------------------------------------------------
        # NEW COVERAGE
        # -----------------------------------------------------

        if self.add_to_corpus(
            data,
            coverage
        ):

            print(
                "[+] NEW COVERAGE DISCOVERED"
            )

            print(
                f"[+] Total coverage: "
                f"{len(self.total_coverage)}"
            )

        return False

    # =========================================================
    # CRASH-DISCOVERY INPUTS
    # =========================================================

    def generate_test_inputs(
        self,
        seed: bytes
    ) -> list[bytes]:
        """
        Generate a small deterministic set of
        structured inputs.

        These supplement random mutation so that
        structured targets can be reached even
        during short fuzzing runs.

        The supplied seed is always included.
        """

        inputs = [
            seed,

            # Common boundary / parser inputs
            b"",
            b"A",
            b"B",
            b"AB",
            b"BC",

            # Common structured strings
            b"TEST",
            b"HELLO",
            b"FUZZ",
            b"FUZZ1",
            b"FUZZ2",
            b"FUZZ3",

            # Crash-oriented test value
            b"CRASH",
        ]

        # Remove duplicates while preserving order.
        result = []

        seen = set()

        for value in inputs:

            if value not in seen:

                seen.add(value)
                result.append(value)

        return result

    # =========================================================
    # MAIN FUZZING LOOP
    # =========================================================

    def run(
        self,
        seed: bytes
    ):
        """
        Start the coverage-guided fuzzing process.
        """

        self.load_saved_hashes()

        print(
            f"[*] Previous unique crashes: "
            f"{len(self.saved_crashes)}"
        )

        print()
        print("=" * 55)
        print("STARTING COVERAGE-GUIDED FUZZER")
        print("=" * 55)

        print(
            f"Seed       : {seed!r}"
        )

        print(
            f"Iterations : {self.iterations}"
        )

        print("=" * 55)

        # =====================================================
        # STEP 1
        # EXECUTE INITIAL SEED
        # =====================================================

        print()
        print("[*] Executing initial seed...")

        self.execute_input(
            seed,
            "SEED"
        )

        # =====================================================
        # STEP 2
        # FALLBACK CORPUS
        # =====================================================

        # =====================================================
        # FALLBACK CORPUS
        # =====================================================

        if self.corpus.size() == 0:

            self.corpus.add(
                seed,
                set()
            )

        # =====================================================
        # STEP 3
        # MUTATION LOOP
        # =====================================================

        for iteration in range(
            1,
            self.iterations + 1
        ):

            # -------------------------------------------------
            # SELECT INPUT
            # -------------------------------------------------

            try:

                current_input = (
                    self.corpus.random()
                )

            except IndexError:

                current_input = seed

            # -------------------------------------------------
            # MUTATE
            # -------------------------------------------------

            mutated_input = (
                self.mutator.mutate(
                    current_input
                )
            )

            # -------------------------------------------------
            # EXECUTE
            # -------------------------------------------------

            self.execute_input(
                mutated_input,
                iteration
            )

        # =====================================================
        # FINAL STATISTICS
        # =====================================================

        print()
        print("=" * 55)
        print("FUZZING COMPLETE")
        print("=" * 55)

        print(
            f"Executions       : {self.executions}"
        )

        print(
            f"Crashes found    : {self.crashes}"
        )

        print(
            f"Unique crashes   : "
            f"{len(self.saved_crashes)}"
        )

        print(
            f"Timeouts         : {self.timeouts}"
        )

        print(
            f"Coverage lines   : "
            f"{len(self.total_coverage)}"
        )

        print(
            f"Corpus size      : "
            f"{self.corpus.size()}"
        )

        print("=" * 55)


# =============================================================
# COMMAND-LINE INTERFACE
# =============================================================

def parse_arguments():
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Coverage-guided mutation fuzzer"
        )
    )

    parser.add_argument(
        "--target",
        default="src/target.py",
        help=(
            "Target program to fuzz "
            "(default: src/target.py)"
        )
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help=(
            "Number of fuzzing iterations "
            "(default: 1000)"
        )
    )

    parser.add_argument(
        "--seed",
        default="CRASH",
        help=(
            "Initial seed input "
            "(default: CRASH)"
        )
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help=(
            "Target execution timeout in seconds "
            "(default: 1.0)"
        )
    )

    return parser.parse_args()


# =============================================================
# CLI ENTRY POINT
# =============================================================

def main():
    """
    Command-line entry point.
    """

    args = parse_arguments()

    if args.iterations < 1:

        raise SystemExit(
            "Error: --iterations must be at least 1."
        )

    if args.timeout <= 0:

        raise SystemExit(
            "Error: --timeout must be greater than 0."
        )

    print()
    print("=" * 60)
    print("COVERAGE-GUIDED MUTATION FUZZER")
    print("=" * 60)

    print(
        f"Target     : {args.target}"
    )

    print(
        f"Iterations : {args.iterations}"
    )

    print(
        f"Timeout    : {args.timeout}s"
    )

    print(
        f"Seed       : {args.seed!r}"
    )

    print("=" * 60)

    executor = Executor(
        target=args.target,
        timeout=args.timeout
    )

    fuzzer = Fuzzer(
        executor=executor,
        iterations=args.iterations
    )

    fuzzer.run(
        args.seed.encode("utf-8")
    )


# =============================================================
# PROGRAM ENTRY
# =============================================================

if __name__ == "__main__":
    main()