import subprocess
import sys
import time
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Any


class ExecutionStatus(Enum):
    """
    Result of executing the target.
    """

    NORMAL = "normal"
    CRASH = "crash"
    TIMEOUT = "timeout"


@dataclass
class ExecutionResult:
    """
    Stores information about one target execution.
    """

    status: ExecutionStatus
    exit_code: int | None = None
    stdout: bytes = b""
    stderr: bytes = b""
    duration: float = 0.0
    coverage: set = field(default_factory=set)


class Executor:
    """
    Executes a fuzzing target.

    The target can be either:

    1. A Python script path:

           Executor("src/target.py")

    2. A Python callable:

           Executor(target_function)

    For script targets, execution happens in a separate
    Python process and line coverage is collected inside
    that process.
    """

    def __init__(
        self,
        target: str | Path | Callable[[bytes], Any],
        timeout: float = 1.0
    ):
        self.target = target
        self.timeout = timeout

    # =========================================================
    # MAIN EXECUTION
    # =========================================================

    def run(self, data: bytes) -> ExecutionResult:
        """
        Execute the target with the supplied input.
        """

        if not isinstance(data, bytes):
            data = bytes(data)

        if callable(self.target):
            return self._run_callable(data)

        return self._run_script(data)

    # =========================================================
    # CALLABLE TARGET
    # =========================================================

    def _run_callable(
        self,
        data: bytes
    ) -> ExecutionResult:
        """
        Execute a Python callable target.
        """

        start = time.perf_counter()

        try:

            result = self.target(data)

            duration = time.perf_counter() - start

            if isinstance(result, ExecutionResult):

                if result.duration == 0.0:
                    result.duration = duration

                return result

            stdout = b""

            if result is not None:

                if isinstance(result, bytes):
                    stdout = result

                elif isinstance(result, str):
                    stdout = result.encode()

                else:
                    stdout = str(result).encode()

            return ExecutionResult(
                status=ExecutionStatus.NORMAL,
                exit_code=0,
                stdout=stdout,
                stderr=b"",
                duration=duration,
                coverage=set(),
            )

        except TimeoutError as error:

            duration = time.perf_counter() - start

            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                exit_code=None,
                stdout=b"",
                stderr=str(error).encode(),
                duration=duration,
                coverage=set(),
            )

        except Exception as error:

            duration = time.perf_counter() - start

            return ExecutionResult(
                status=ExecutionStatus.CRASH,
                exit_code=1,
                stdout=b"",
                stderr=str(error).encode(),
                duration=duration,
                coverage=set(),
            )

    # =========================================================
    # SCRIPT TARGET
    # =========================================================

    def _run_script(
        self,
        data: bytes
    ) -> ExecutionResult:
        """
        Execute a Python script in a separate process.

        A small wrapper is executed around target.py.

        The wrapper:

            1. Starts Python tracing.
            2. Executes target.py.
            3. Records target.py line numbers.
            4. Writes the coverage to a temporary file.
            5. Preserves the target's exit status.

        This is necessary because sys.settrace() in the
        parent process cannot trace a separate subprocess.
        """

        target_path = Path(self.target).resolve()

        # -----------------------------------------------------
        # TEMPORARY COVERAGE FILE
        # -----------------------------------------------------

        coverage_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".coverage",
            delete=False,
            encoding="utf-8"
        )

        coverage_path = Path(
            coverage_file.name
        )

        coverage_file.close()

        # -----------------------------------------------------
        # COVERAGE WRAPPER
        # -----------------------------------------------------

        wrapper = r'''
import runpy
import sys


target_path = sys.argv[1]
coverage_path = sys.argv[2]

covered_lines = set()


def trace(frame, event, arg):
    """
    Record executed lines belonging to target.py.
    """

    if event == "line":

        filename = frame.f_code.co_filename

        if filename == target_path:
            covered_lines.add(
                frame.f_lineno
            )

    return trace


sys.settrace(trace)

try:

    runpy.run_path(
        target_path,
        run_name="__main__"
    )

finally:

    sys.settrace(None)

    with open(
        coverage_path,
        "w",
        encoding="utf-8"
    ) as file:

        for line in sorted(covered_lines):
            file.write(
                f"{line}\n"
            )
'''

        # -----------------------------------------------------
        # COMMAND
        # -----------------------------------------------------

        command = [
            sys.executable,
            "-c",
            wrapper,
            str(target_path),
            str(coverage_path),
        ]

        start = time.perf_counter()

        try:

            process = subprocess.run(
                command,
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
            )

            duration = (
                time.perf_counter()
                - start
            )

        except subprocess.TimeoutExpired as error:

            duration = (
                time.perf_counter()
                - start
            )

            stdout = error.stdout or b""
            stderr = error.stderr or b""

            if isinstance(stdout, str):
                stdout = stdout.encode()

            if isinstance(stderr, str):
                stderr = stderr.encode()

            coverage = self._read_coverage(
                coverage_path
            )

            self._delete_coverage_file(
                coverage_path
            )

            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                coverage=coverage,
            )

        except OSError as error:

            duration = (
                time.perf_counter()
                - start
            )

            self._delete_coverage_file(
                coverage_path
            )

            return ExecutionResult(
                status=ExecutionStatus.CRASH,
                exit_code=None,
                stdout=b"",
                stderr=str(error).encode(),
                duration=duration,
                coverage=set(),
            )

        # -----------------------------------------------------
        # READ COVERAGE
        # -----------------------------------------------------

        coverage = self._read_coverage(
            coverage_path
        )

        self._delete_coverage_file(
            coverage_path
        )

        # =====================================================
        # NORMAL EXIT
        # =====================================================

        if process.returncode == 0:

            return ExecutionResult(
                status=ExecutionStatus.NORMAL,
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                duration=duration,
                coverage=coverage,
            )

        # =====================================================
        # NON-ZERO EXIT = CRASH
        # =====================================================

        return ExecutionResult(
            status=ExecutionStatus.CRASH,
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
            duration=duration,
            coverage=coverage,
        )

    # =========================================================
    # READ COVERAGE
    # =========================================================

    def _read_coverage(
        self,
        coverage_path: Path
    ) -> set:
        """
        Read coverage line numbers produced by the
        subprocess wrapper.
        """

        coverage = set()

        if not coverage_path.exists():
            return coverage

        try:

            with coverage_path.open(
                "r",
                encoding="utf-8"
            ) as file:

                for line in file:

                    line = line.strip()

                    if not line:
                        continue

                    try:
                        coverage.add(
                            int(line)
                        )

                    except ValueError:
                        continue

        except OSError:
            pass

        return coverage

    # =========================================================
    # DELETE COVERAGE FILE
    # =========================================================

    def _delete_coverage_file(
        self,
        coverage_path: Path
    ):
        """
        Remove temporary coverage file.
        """

        try:

            if coverage_path.exists():
                coverage_path.unlink()

        except OSError:
            pass

    # =========================================================
    # CONVENIENCE ALIAS
    # =========================================================

    def execute(
        self,
        data: bytes
    ) -> ExecutionResult:
        """
        Alias for run().
        """

        return self.run(data)

    # =========================================================
    # STATUS HELPERS
    # =========================================================

    def is_crash(
        self,
        result: ExecutionResult
    ) -> bool:
        """
        Return True if execution crashed.
        """

        return (
            result.status
            == ExecutionStatus.CRASH
        )

    def is_timeout(
        self,
        result: ExecutionResult
    ) -> bool:
        """
        Return True if execution timed out.
        """

        return (
            result.status
            == ExecutionStatus.TIMEOUT
        )

    def is_normal(
        self,
        result: ExecutionResult
    ) -> bool:
        """
        Return True if execution completed normally.
        """

        return (
            result.status
            == ExecutionStatus.NORMAL
        )