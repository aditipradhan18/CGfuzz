from __future__ import annotations

import os
import re
import runpy
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Union


# ============================================================
# EXECUTION STATUS
# ============================================================

class ExecutionStatus(Enum):
    NORMAL = "normal"
    CRASH = "crash"
    TIMEOUT = "timeout"


# ============================================================
# EXECUTION RESULT
# ============================================================

@dataclass
class ExecutionResult:
    status: ExecutionStatus
    exit_code: int
    stderr: bytes = b""
    stdout: bytes = b""
    duration: float = 0.0
    coverage: set = field(default_factory=set)

    @property
    def output(self) -> bytes:
        return self.stdout

    @property
    def crashed(self) -> bool:
        return self.status == ExecutionStatus.CRASH

    @property
    def timed_out(self) -> bool:
        return self.status == ExecutionStatus.TIMEOUT

    @property
    def normal(self) -> bool:
        return self.status == ExecutionStatus.NORMAL


# ============================================================
# EXECUTOR
# ============================================================

class Executor:
    """
    Execute Python or native targets in an isolated subprocess.

    Supported targets:
        - Python script (.py)
        - Native executable (.exe / binary)
        - Python callable

    Native targets can optionally provide GCC/gcov coverage
    when compiled with coverage instrumentation.
    """

    def __init__(
        self,
        target: Union[str, Path, Callable],
        timeout: float = 1.0,
    ):
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.target = target
        self.timeout = float(timeout)

        self._is_callable = callable(target)

        if self._is_callable:
            self.target_path: Optional[Path] = None
        else:
            self.target_path = Path(target)

    # ========================================================
    # MAIN EXECUTION API
    # ========================================================

    def run(self, data: bytes) -> ExecutionResult:
        """
        Execute target with supplied input.
        """

        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")

        start = time.perf_counter()

        if self._is_callable:
            return self._run_callable(data, start)

        if self.target_path is None:
            raise RuntimeError("Invalid target")

        if not self.target_path.exists():
            raise FileNotFoundError(
                f"Target not found: {self.target_path}"
            )

        if self._is_python_target():
            return self._run_python_target(data, start)

        return self._run_native_target(data, start)

    # ========================================================
    # CALLABLE TARGET
    # ========================================================

    def _run_callable(
        self,
        data: bytes,
        start: float,
    ) -> ExecutionResult:
        """
        Execute a Python callable.

        This path is mainly used by unit tests and programmatic
        integrations.
        """

        stdout = b""
        stderr = b""

        try:
            result = self.target(data)

            if result is not None:
                if isinstance(result, bytes):
                    stdout = result
                else:
                    stdout = str(result).encode()

            duration = time.perf_counter() - start

            return ExecutionResult(
                status=ExecutionStatus.NORMAL,
                exit_code=0,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                coverage=set(),
            )

        except BaseException as exc:
            duration = time.perf_counter() - start

            message = f"{type(exc).__name__}: {exc}"

            return ExecutionResult(
                status=ExecutionStatus.CRASH,
                exit_code=1,
                stdout=stdout,
                stderr=message.encode(),
                duration=duration,
                coverage=set(),
            )

    # ========================================================
    # PYTHON TARGET
    # ========================================================

    def _run_python_target(
        self,
        data: bytes,
        start: float,
    ) -> ExecutionResult:
        """
        Execute a Python target in a child process.

        Line coverage is collected using sys.settrace().
        """

        coverage_file = tempfile.NamedTemporaryFile(
            suffix=".coverage",
            delete=False,
        )

        coverage_path = Path(coverage_file.name)
        coverage_file.close()

        wrapper = self._create_python_wrapper(
            self.target_path,
            coverage_path,
        )

        try:
            completed = subprocess.run(
                [sys.executable, str(wrapper)],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
            )

            duration = time.perf_counter() - start

            coverage = self._read_python_coverage(
                coverage_path
            )

            if completed.returncode == 0:
                status = ExecutionStatus.NORMAL
            else:
                status = ExecutionStatus.CRASH

            return ExecutionResult(
                status=status,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration=duration,
                coverage=coverage,
            )

        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - start

            stdout = self._safe_bytes(exc.stdout)
            stderr = self._safe_bytes(exc.stderr)

            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                exit_code=-1,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                coverage=set(),
            )

        except OSError as exc:
            duration = time.perf_counter() - start

            return ExecutionResult(
                status=ExecutionStatus.CRASH,
                exit_code=-1,
                stdout=b"",
                stderr=str(exc).encode(),
                duration=duration,
                coverage=set(),
            )

        finally:
            try:
                coverage_path.unlink(missing_ok=True)
            except OSError:
                pass

            try:
                wrapper.unlink(missing_ok=True)
            except OSError:
                pass

    # ========================================================
    # PYTHON WRAPPER
    # ========================================================

    def _create_python_wrapper(
        self,
        target_path: Path,
        coverage_path: Path,
    ) -> Path:
        """
        Create a temporary Python wrapper which:

        1. Reads stdin through the target itself.
        2. Installs a line tracer.
        3. Executes the target.
        4. Saves executed target lines.
        """

        wrapper = Path(
            tempfile.mktemp(
                prefix="cgfuzz_wrapper_",
                suffix=".py",
            )
        )

        target = str(target_path.resolve()).replace(
            "\\",
            "\\\\",
        )

        coverage = str(coverage_path.resolve()).replace(
            "\\",
            "\\\\",
        )

        source = f'''
import sys
import runpy

TARGET = r"{target}"
COVERAGE = r"{coverage}"

executed = set()


def trace(frame, event, arg):
    if event == "line":
        filename = frame.f_code.co_filename

        try:
            if filename == TARGET:
                executed.add(frame.f_lineno)
        except Exception:
            pass

    return trace


sys.settrace(trace)

try:
    runpy.run_path(
        TARGET,
        run_name="__main__",
    )
finally:
    sys.settrace(None)

    try:
        with open(
            COVERAGE,
            "w",
            encoding="utf-8",
        ) as f:
            for line in sorted(executed):
                f.write(str(line) + "\\n")
    except Exception:
        pass
'''

        wrapper.write_text(
            source,
            encoding="utf-8",
        )

        return wrapper

    # ========================================================
    # PYTHON COVERAGE READER
    # ========================================================

    def _read_python_coverage(
        self,
        coverage_path: Path,
    ) -> set:
        """
        Read line numbers produced by the Python tracer.
        """

        coverage = set()

        if not coverage_path.exists():
            return coverage

        try:
            content = coverage_path.read_text(
                encoding="utf-8",
            )

            for line in content.splitlines():
                line = line.strip()

                if line.isdigit():
                    coverage.add(int(line))

        except (OSError, ValueError):
            pass

        return coverage

    # ========================================================
    # NATIVE TARGET
    # ========================================================

    def _run_native_target(
        self,
        data: bytes,
        start: float,
    ) -> ExecutionResult:
        """
        Execute a native target such as a Windows .exe.

        After execution, attempt to collect GCC/gcov coverage
        if the target was compiled with coverage instrumentation.
        """

        try:
            completed = subprocess.run(
                [str(self.target_path)],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
                cwd=str(self.target_path.parent),
            )

            duration = time.perf_counter() - start

            coverage = self._collect_native_coverage()

            if completed.returncode == 0:
                status = ExecutionStatus.NORMAL
            else:
                status = ExecutionStatus.CRASH

            return ExecutionResult(
                status=status,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration=duration,
                coverage=coverage,
            )

        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - start

            stdout = self._safe_bytes(exc.stdout)
            stderr = self._safe_bytes(exc.stderr)

            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                exit_code=-1,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                coverage=set(),
            )

        except OSError as exc:
            duration = time.perf_counter() - start

            return ExecutionResult(
                status=ExecutionStatus.CRASH,
                exit_code=-1,
                stdout=b"",
                stderr=str(exc).encode(),
                duration=duration,
                coverage=set(),
            )

    # ========================================================
    # NATIVE COVERAGE COLLECTION
    # ========================================================

    def _collect_native_coverage(self) -> set:
        """
        Collect line coverage from a GCC/gcov-instrumented
        native target.

        gcov generates files such as:

            vulnerable.c.gcov

        The parser extracts executed source line numbers.
        """

        coverage = set()

        if self.target_path is None:
            return coverage

        target_dir = self.target_path.parent

        try:
            source_files = self._find_native_sources(
                target_dir
            )

            if not source_files:
                return coverage

            for source in source_files:
                self._run_gcov(
                    source,
                    target_dir,
                )

            gcov_files = list(
                target_dir.glob("*.gcov")
            )

            for gcov_file in gcov_files:
                coverage.update(
                    self._parse_gcov_file(
                        gcov_file
                    )
                )

        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return coverage

        return coverage

    # ========================================================
    # FIND NATIVE SOURCES
    # ========================================================

    def _find_native_sources(
        self,
        directory: Path,
    ) -> list[Path]:
        """
        Find C/C++ source files associated with the native
        target.
        """

        extensions = {
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
        }

        sources = []

        try:
            for path in directory.iterdir():
                if (
                    path.is_file()
                    and path.suffix.lower() in extensions
                ):
                    sources.append(path)

        except OSError:
            pass

        return sources

    # ========================================================
    # RUN GCOV
    # ========================================================

    def _run_gcov(
        self,
        source: Path,
        directory: Path,
    ) -> None:
        """
        Run gcov against a source file.

        gcov is optional. If unavailable, native execution
        continues and coverage remains empty.
        """

        try:
            subprocess.run(
                [
                    "gcov",
                    "-b",
                    "-c",
                    "-o",
                    str(directory),
                    str(source),
                ],
                cwd=str(directory),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5.0,
                check=False,
            )

        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            OSError,
        ):
            pass

    # ========================================================
    # GCOV PARSER
    # ========================================================

    def _parse_gcov_file(
        self,
        gcov_path: Path,
    ) -> set:
        """
        Parse a .gcov file.

        Examples:

            1:   41: if (input[0] == 'F')
            -:   42: unused source line
            #####: 44: vulnerable_branch();

        Only executable lines with an execution count greater
        than zero are included.
        """

        coverage = set()

        if not gcov_path.exists():
            return coverage

        try:
            text = gcov_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        except OSError:
            return coverage

        for line in text.splitlines():

            match = re.match(
                r"^\s*([^:]+):\s*(\d+):",
                line,
            )

            if not match:
                continue

            count_text = match.group(1).strip()
            line_number = int(match.group(2))

            # Non-executable line.
            if count_text == "-":
                continue

            # Executable but never executed.
            if "#" in count_text:
                continue

            try:
                count = int(count_text)

            except ValueError:
                continue

            if count > 0:
                coverage.add(line_number)

        return coverage

    # ========================================================
    # TARGET TYPE
    # ========================================================

    def _is_python_target(self) -> bool:
        """
        Return True when the configured target is a Python
        script.
        """

        if self.target_path is None:
            return False

        return self.target_path.suffix.lower() == ".py"

    # ========================================================
    # SAFE BYTE CONVERSION
    # ========================================================

    @staticmethod
    def _safe_bytes(value) -> bytes:
        """
        Convert subprocess output to bytes safely.
        """

        if value is None:
            return b""

        if isinstance(value, bytes):
            return value

        if isinstance(value, str):
            return value.encode()

        try:
            return bytes(value)

        except Exception:
            return b""

    # ========================================================
    # STATUS HELPERS
    # ========================================================

    def is_crash(
        self,
        result: ExecutionResult,
    ) -> bool:
        """
        Return True if execution crashed.
        """

        return result.status == ExecutionStatus.CRASH

    def is_timeout(
        self,
        result: ExecutionResult,
    ) -> bool:
        """
        Return True if execution timed out.
        """

        return result.status == ExecutionStatus.TIMEOUT

    def is_normal(
        self,
        result: ExecutionResult,
    ) -> bool:
        """
        Return True if execution completed normally.
        """

        return result.status == ExecutionStatus.NORMAL


# ============================================================
# MODULE EXPORTS
# ============================================================

__all__ = [
    "ExecutionStatus",
    "ExecutionResult",
    "Executor",
]