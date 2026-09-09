from __future__ import annotations

import os
import queue
import re
import runpy
import subprocess
import sys
import tempfile
import threading
import time

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Union

from .bitmap import CoverageBitmap


# ============================================================
# EXECUTION STATUS
# ============================================================


class ExecutionStatus(Enum):
    """
    Result status of one target execution.
    """

    NORMAL = "normal"
    CRASH = "crash"
    TIMEOUT = "timeout"


# ============================================================
# EXECUTION RESULT
# ============================================================


@dataclass
class ExecutionResult:
    """
    Stores information about one target execution.

    Defaults are intentionally provided for optional fields so
    older tests can construct ExecutionResult objects using only
    status, exit_code and stderr.
    """

    status: ExecutionStatus

    exit_code: int = 0

    stderr: bytes = b""

    stdout: bytes = b""

    duration: float = 0.0

    coverage: set = field(
        default_factory=set
    )

    bitmap: Optional[CoverageBitmap] = None

    sanitizer: Optional[str] = None

    sanitizer_message: str = ""

    # ---------------------------------------------------------
    # COMPATIBILITY HELPERS
    # ---------------------------------------------------------

    @property
    def output(self) -> bytes:
        """
        Backward-compatible alias for stdout.
        """

        return self.stdout

    @property
    def crashed(self) -> bool:
        """
        Return True when execution crashed.
        """

        return (
            self.status
            == ExecutionStatus.CRASH
        )

    @property
    def timed_out(self) -> bool:
        """
        Return True when execution timed out.
        """

        return (
            self.status
            == ExecutionStatus.TIMEOUT
        )

    @property
    def normal(self) -> bool:
        """
        Return True when execution completed normally.
        """

        return (
            self.status
            == ExecutionStatus.NORMAL
        )


# ============================================================
# EXECUTOR
# ============================================================


class Executor:
    """
    Execute Python scripts, native executables, or Python
    callable targets.

    Supported:

        Executor("src/target.py")

        Executor("native_targets/vulnerable.exe")

        Executor(my_python_function)

    Features:

        - subprocess isolation
        - timeout handling
        - Python line coverage
        - Python edge coverage
        - bitmap coverage
        - native gcov coverage
        - ASan detection
        - UBSan detection
        - callable targets for unit tests
        - persistent Python execution mode
    """

    def __init__(
        self,
        target: Union[
            str,
            Path,
            Callable
        ],
        timeout: float = 1.0,
        sanitizers: tuple[str, ...] = (),
        persistent: bool = False
    ):
        # =====================================================
        # VALIDATE TIMEOUT
        # =====================================================

        if timeout <= 0:
            raise ValueError(
                "timeout must be greater than zero"
            )

        # =====================================================
        # STORE CONFIGURATION
        # =====================================================

        self.target = target

        self.timeout = float(
            timeout
        )

        self.persistent = bool(
            persistent
        )

        self.sanitizers = tuple(
            sanitizer.lower()
            for sanitizer in sanitizers
        )

        # =====================================================
        # VALID SANITIZERS
        # =====================================================

        valid_sanitizers = {
            "asan",
            "ubsan",
        }

        invalid = (
            set(self.sanitizers)
            - valid_sanitizers
        )

        if invalid:
            raise ValueError(
                f"Unsupported sanitizers: "
                f"{sorted(invalid)}"
            )

        # =====================================================
        # TARGET TYPE
        # =====================================================

        self._is_callable = callable(
            target
        )

        if self._is_callable:

            self.target_callable = target

            self.target_path = None

        else:

            self.target_callable = None

            self.target_path = (
                Path(target).resolve()
            )

        # =====================================================
        # PERSISTENT WORKER STATE
        # =====================================================

        self._persistent_process = None

        self._persistent_stdin = None

        self._persistent_stdout = None

        self._persistent_stderr = None

        self._persistent_lock = (
            threading.Lock()
        )

    # =========================================================
    # MAIN EXECUTION API
    # =========================================================

    def run(
        self,
        data: bytes
    ) -> ExecutionResult:
        """
        Execute one input.
        """

        if not isinstance(data, bytes):

            raise TypeError(
                "data must be bytes"
            )

        start = (
            time.perf_counter()
        )

        # -----------------------------------------------------
        # CALLABLE TARGET
        # -----------------------------------------------------

        if self._is_callable:

            return self._run_callable(
                data,
                start
            )

        # -----------------------------------------------------
        # TARGET VALIDATION
        # -----------------------------------------------------

        if self.target_path is None:

            raise RuntimeError(
                "Invalid target"
            )

        if not self.target_path.exists():

            raise FileNotFoundError(
                f"Target not found: "
                f"{self.target_path}"
            )

        # -----------------------------------------------------
        # PERSISTENT PYTHON MODE
        # -----------------------------------------------------

        if (
            self.persistent
            and self._is_python_target()
        ):

            return self._run_python_persistent(
                data,
                start
            )

        # -----------------------------------------------------
        # PYTHON SCRIPT
        # -----------------------------------------------------

        if self._is_python_target():

            return self._run_python_target(
                data,
                start
            )

        # -----------------------------------------------------
        # NATIVE EXECUTABLE
        # -----------------------------------------------------

        return self._run_native_target(
            data,
            start
        )

    # =========================================================
    # CALLABLE TARGET
    # =========================================================

    def _run_callable(
        self,
        data: bytes,
        start: float
    ) -> ExecutionResult:
        """
        Execute a Python callable directly.

        This is intentionally lightweight and exists primarily
        for unit tests and simple programmatic targets.
        """

        stdout = b""

        stderr = b""

        try:

            result = self.target_callable(
                data
            )

            # -------------------------------------------------
            # CONVERT RETURN VALUE
            # -------------------------------------------------

            if result is None:

                stdout = b""

            elif isinstance(
                result,
                bytes
            ):

                stdout = result

            else:

                stdout = str(
                    result
                ).encode(
                    errors="replace"
                )

            duration = (
                time.perf_counter()
                - start
            )

            return ExecutionResult(
                status=ExecutionStatus.NORMAL,
                exit_code=0,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                coverage=set(),
                bitmap=None,
                sanitizer=None,
                sanitizer_message="",
            )

        except BaseException as exc:

            duration = (
                time.perf_counter()
                - start
            )

            message = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            stderr = message.encode(
                errors="replace"
            )

            return ExecutionResult(
                status=ExecutionStatus.CRASH,
                exit_code=1,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                coverage=set(),
                bitmap=None,
                sanitizer=None,
                sanitizer_message="",
            )

    # =========================================================
    # PYTHON TARGET
    # =========================================================

    def _run_python_target(
        self,
        data: bytes,
        start: float
    ) -> ExecutionResult:
        """
        Execute a Python target in an isolated subprocess.

        The subprocess wrapper collects:

            - line coverage
            - edge coverage

        Edge coverage is subsequently converted into a bitmap.
        """

        coverage_file = (
            tempfile.NamedTemporaryFile(
                suffix=".coverage",
                delete=False,
            )
        )

        coverage_path = Path(
            coverage_file.name
        )

        coverage_file.close()

        wrapper = (
            self._create_python_wrapper(
                self.target_path,
                coverage_path
            )
        )

        try:

            completed = subprocess.run(
                [
                    sys.executable,
                    str(wrapper),
                ],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
            )

            duration = (
                time.perf_counter()
                - start
            )

            coverage, edges = (
                self._read_python_coverage(
                    coverage_path
                )
            )

            bitmap = (
                self._build_bitmap(
                    edges
                )
            )

            if completed.returncode == 0:

                status = (
                    ExecutionStatus.NORMAL
                )

            else:

                status = (
                    ExecutionStatus.CRASH
                )

            return ExecutionResult(
                status=status,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration=duration,
                coverage=coverage,
                bitmap=bitmap,
                sanitizer=None,
                sanitizer_message="",
            )

        except subprocess.TimeoutExpired as exc:

            duration = (
                time.perf_counter()
                - start
            )

            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                exit_code=-1,
                stdout=self._safe_bytes(
                    exc.stdout
                ),
                stderr=self._safe_bytes(
                    exc.stderr
                ),
                duration=duration,
                coverage=set(),
                bitmap=None,
                sanitizer=None,
                sanitizer_message="",
            )

        except OSError as exc:

            duration = (
                time.perf_counter()
                - start
            )

            return ExecutionResult(
                status=ExecutionStatus.CRASH,
                exit_code=-1,
                stdout=b"",
                stderr=str(exc).encode(
                    errors="replace"
                ),
                duration=duration,
                coverage=set(),
                bitmap=None,
                sanitizer=None,
                sanitizer_message="",
            )

        finally:

            try:

                coverage_path.unlink(
                    missing_ok=True
                )

            except OSError:

                pass

            try:

                wrapper.unlink(
                    missing_ok=True
                )

            except OSError:

                pass

    # =========================================================
    # PYTHON WRAPPER
    # =========================================================

    def _create_python_wrapper(
        self,
        target_path: Path,
        coverage_path: Path
    ) -> Path:
        """
        Create a temporary Python wrapper.

        The wrapper:

            1. installs sys.settrace()
            2. executes the target
            3. records target lines
            4. records consecutive-line edges
            5. writes coverage information
        """

        wrapper = Path(
            tempfile.mktemp(
                prefix="cgfuzz_wrapper_",
                suffix=".py",
            )
        )

        target = str(
            target_path.resolve()
        ).replace(
            "\\",
            "\\\\"
        )

        coverage = str(
            coverage_path.resolve()
        ).replace(
            "\\",
            "\\\\"
        )

        source = f'''
import os
import runpy
import sys

TARGET = os.path.abspath(
    r"{target}"
)

COVERAGE = r"{coverage}"

executed = set()

edges = set()

previous_line = None

previous_filename = None


def trace(frame, event, arg):

    global previous_line
    global previous_filename

    if event == "line":

        filename = os.path.abspath(
            frame.f_code.co_filename
        )

        if filename == TARGET:

            current_line = frame.f_lineno

            # -----------------------------------------------
            # LINE COVERAGE
            # -----------------------------------------------

            executed.add(
                current_line
            )

            # -----------------------------------------------
            # EDGE COVERAGE
            # -----------------------------------------------

            if (
                previous_line is not None
                and previous_filename == TARGET
            ):

                edge_id = (
                    (previous_line << 32)
                    ^ current_line
                )

                edges.add(
                    edge_id
                )

            previous_line = current_line

            previous_filename = TARGET

        else:

            previous_line = None

            previous_filename = filename

    return trace


sys.settrace(trace)

try:

    runpy.run_path(
        TARGET,
        run_name="__main__"
    )

finally:

    sys.settrace(None)

    try:

        with open(
            COVERAGE,
            "w",
            encoding="utf-8"
        ) as f:

            for line in sorted(
                executed
            ):

                f.write(
                    "L:"
                    + str(line)
                    + "\\n"
                )

            for edge in sorted(
                edges
            ):

                f.write(
                    "E:"
                    + str(edge)
                    + "\\n"
                )

    except Exception:

        pass
'''

        wrapper.write_text(
            source,
            encoding="utf-8"
        )

        return wrapper

    # =========================================================
    # PYTHON COVERAGE READER
    # =========================================================

    def _read_python_coverage(
        self,
        coverage_path: Path
    ) -> tuple[set, set]:
        """
        Read line and edge coverage.
        """

        coverage = set()

        edges = set()

        if not coverage_path.exists():

            return coverage, edges

        try:

            content = (
                coverage_path.read_text(
                    encoding="utf-8"
                )
            )

            for line in content.splitlines():

                line = line.strip()

                # ---------------------------------------------
                # LINE
                # ---------------------------------------------

                if line.startswith("L:"):

                    value = line[2:]

                    if value.isdigit():

                        coverage.add(
                            int(value)
                        )

                # ---------------------------------------------
                # EDGE
                # ---------------------------------------------

                elif line.startswith("E:"):

                    value = line[2:]

                    try:

                        edges.add(
                            int(value)
                        )

                    except ValueError:

                        pass

        except (
            OSError,
            ValueError
        ):

            pass

        return coverage, edges

    # =========================================================
    # BUILD BITMAP
    # =========================================================

    def _build_bitmap(
        self,
        edges: set
    ) -> CoverageBitmap:
        """
        Convert edge IDs into a coverage bitmap.
        """

        bitmap = CoverageBitmap()

        for edge_id in edges:

            bitmap.record(
                edge_id
            )

        return bitmap

    # =========================================================
    # NATIVE SANITIZER ENVIRONMENT
    # =========================================================

    def _get_native_environment(self):
        """
        Build the environment for native targets.

        When ASan or UBSan is enabled, the LLVM runtime
        directory is prepended to PATH.
        """

        environment = (
            os.environ.copy()
        )

        if not self.sanitizers:

            return environment

        sanitizer_lib = (
            os.environ.get(
                "CGFUZZ_SANITIZER_LIB"
            )
        )

        if not sanitizer_lib:

            raise RuntimeError(
                "CGFUZZ_SANITIZER_LIB is required "
                "when sanitizers are enabled"
            )

        existing_path = (
            environment.get(
                "PATH",
                ""
            )
        )

        environment["PATH"] = (
            sanitizer_lib
            + os.pathsep
            + existing_path
        )

        return environment

    # =========================================================
    # SANITIZER DETECTION
    # =========================================================

    def _detect_sanitizer(
        self,
        stderr: bytes
    ) -> tuple[Optional[str], str]:
        """
        Detect ASan or UBSan diagnostics.
        """

        if not stderr:

            return None, ""

        text = stderr.decode(
            "utf-8",
            errors="replace"
        )

        # -----------------------------------------------------
        # ASAN
        # -----------------------------------------------------

        if (
            "AddressSanitizer:"
            in text
            or "ERROR: AddressSanitizer"
            in text
        ):

            return (
                "asan",
                text.strip()
            )

        # -----------------------------------------------------
        # UBSAN
        # -----------------------------------------------------

        if (
            "UndefinedBehaviorSanitizer:"
            in text
            or "runtime error:"
            in text
        ):

            return (
                "ubsan",
                text.strip()
            )

        return None, ""

    # =========================================================
    # NATIVE TARGET
    # =========================================================

    def _run_native_target(
        self,
        data: bytes,
        start: float
    ) -> ExecutionResult:
        """
        Execute a native executable.
        """

        try:

            completed = subprocess.run(
                [
                    str(
                        self.target_path
                    )
                ],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
                cwd=str(
                    self.target_path.parent
                ),
                env=self._get_native_environment(),
            )

            duration = (
                time.perf_counter()
                - start
            )

            coverage = (
                self._collect_native_coverage()
            )

            sanitizer, sanitizer_message = (
                self._detect_sanitizer(
                    completed.stderr
                )
            )

            # -------------------------------------------------
            # SANITIZER CRASH TAKES PRIORITY
            # -------------------------------------------------

            if sanitizer is not None:

                status = (
                    ExecutionStatus.CRASH
                )

            elif completed.returncode == 0:

                status = (
                    ExecutionStatus.NORMAL
                )

            else:

                status = (
                    ExecutionStatus.CRASH
                )

            return ExecutionResult(
                status=status,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration=duration,
                coverage=coverage,
                bitmap=None,
                sanitizer=sanitizer,
                sanitizer_message=sanitizer_message,
            )

        except subprocess.TimeoutExpired as exc:

            duration = (
                time.perf_counter()
                - start
            )

            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                exit_code=-1,
                stdout=self._safe_bytes(
                    exc.stdout
                ),
                stderr=self._safe_bytes(
                    exc.stderr
                ),
                duration=duration,
                coverage=set(),
                bitmap=None,
                sanitizer=None,
                sanitizer_message="",
            )

        except OSError as exc:

            duration = (
                time.perf_counter()
                - start
            )

            return ExecutionResult(
                status=ExecutionStatus.CRASH,
                exit_code=-1,
                stdout=b"",
                stderr=str(exc).encode(
                    errors="replace"
                ),
                duration=duration,
                coverage=set(),
                bitmap=None,
                sanitizer=None,
                sanitizer_message="",
            )

    # =========================================================
    # NATIVE COVERAGE COLLECTION
    # =========================================================

    def _collect_native_coverage(
        self
    ) -> set:
        """
        Collect native line coverage from gcov files.
        """

        coverage = set()

        if self.target_path is None:

            return coverage

        target_dir = (
            self.target_path.parent
        )

        try:

            source_files = (
                self._find_native_sources(
                    target_dir
                )
            )

            if not source_files:

                return coverage

            project_root = (
                target_dir.parent
            )

            for source in source_files:

                self._run_gcov(
                    source,
                    project_root
                )

            # -------------------------------------------------
            # RECURSIVE SEARCH
            # -------------------------------------------------

            gcov_files = list(
                project_root.rglob(
                    "*.gcov"
                )
            )

            for gcov_file in gcov_files:

                coverage.update(
                    self._parse_gcov_file(
                        gcov_file
                    )
                )

        except (
            OSError,
            subprocess.SubprocessError
        ):

            return coverage

        return coverage

    # =========================================================
    # FIND NATIVE SOURCES
    # =========================================================

    def _find_native_sources(
        self,
        directory: Path
    ) -> list[Path]:
        """
        Find C/C++ sources in the native target directory.
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
                    and path.suffix.lower()
                    in extensions
                ):

                    sources.append(
                        path
                    )

        except OSError:

            pass

        return sources

    # =========================================================
    # RUN GCOV
    # =========================================================

    def _run_gcov(
        self,
        source: Path,
        directory: Path
    ) -> None:
        """
        Run gcov for one native source.
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
            OSError
        ):

            pass

    # =========================================================
    # GCOV PARSER
    # =========================================================

    def _parse_gcov_file(
        self,
        gcov_path: Path
    ) -> set:
        """
        Parse a gcov file and return covered line numbers.
        """

        coverage = set()

        if not gcov_path.exists():

            return coverage

        try:

            text = (
                gcov_path.read_text(
                    encoding="utf-8",
                    errors="replace"
                )
            )

        except OSError:

            return coverage

        for line in text.splitlines():

            match = re.match(
                r"^\s*([^:]+):\s*(\d+):",
                line
            )

            if not match:

                continue

            count_text = (
                match.group(1).strip()
            )

            line_number = int(
                match.group(2)
            )

            # -------------------------------------------------
            # NON-CODE
            # -------------------------------------------------

            if count_text == "-":

                continue

            if "#" in count_text:

                continue

            # -------------------------------------------------
            # EXECUTION COUNT
            # -------------------------------------------------

            try:

                count = int(
                    count_text
                )

            except ValueError:

                continue

            if count > 0:

                coverage.add(
                    line_number
                )

        return coverage

    # =========================================================
    # TARGET TYPE
    # =========================================================

    def _is_python_target(
        self
    ) -> bool:
        """
        Return True when target is a Python script.
        """

        if self.target_path is None:

            return False

        return (
            self.target_path
            .suffix
            .lower()
            == ".py"
        )

    # =========================================================
    # PERSISTENT PYTHON WORKER
    # =========================================================

    def _start_persistent_worker(
        self
    ):
        """
        Start a persistent Python worker.

        The target module is loaded once and then reused
        for multiple executions.
        """

        if (
            self._persistent_process is not None
            and self._persistent_process.poll()
            is None
        ):

            return

        worker_source = self._create_persistent_worker()

        process = subprocess.Popen(
            [
                sys.executable,
                str(worker_source),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        self._persistent_process = process

        self._persistent_stdin = (
            process.stdin
        )

        self._persistent_stdout = (
            process.stdout
        )

        self._persistent_stderr = (
            process.stderr
        )

        self._persistent_worker_path = (
            worker_source
        )

    # =========================================================
    # CREATE PERSISTENT WORKER
    # =========================================================

    def _create_persistent_worker(
        self
    ) -> Path:
        """
        Create the Python persistent worker program.

        Protocol:

            parent -> worker:
                4-byte little-endian length
                input bytes

            worker -> parent:
                4-byte output length
                output bytes
                4-byte coverage length
                coverage text
        """

        worker = Path(
            tempfile.mktemp(
                prefix="cgfuzz_persistent_",
                suffix=".py"
            )
        )

        target = str(
            self.target_path.resolve()
        ).replace(
            "\\",
            "\\\\"
        )

        source = f'''
import os
import runpy
import struct
import sys
import traceback

TARGET = os.path.abspath(
    r"{target}"
)

TARGET_NORMALIZED = os.path.normcase(
    os.path.abspath(TARGET)
)


def read_exact(stream, size):

    data = b""

    while len(data) < size:

        chunk = stream.read(
            size - len(data)
        )

        if not chunk:

            return None

        data += chunk

    return data


def send(stream, data):

    stream.write(
        struct.pack(
            "<I",
            len(data)
        )
    )

    if data:

        stream.write(data)

    stream.flush()


# ============================================================
# LOAD TARGET
# ============================================================

namespace = runpy.run_path(
    TARGET,
    run_name="cgfuzz_target"
)

target_function = namespace.get(
    "target"
)

if target_function is None:

    target_function = namespace.get(
        "process"
    )


# ============================================================
# EXECUTION
# ============================================================

while True:

    raw_length = read_exact(
        sys.stdin.buffer,
        4
    )

    if raw_length is None:

        break

    length = struct.unpack(
        "<I",
        raw_length
    )[0]

    data = read_exact(
        sys.stdin.buffer,
        length
    )

    if data is None:

        break

    executed = set()

    edges = set()

    previous_line = None

    previous_filename = None


    def trace(
        frame,
        event,
        arg
    ):

        nonlocal_dummy = None

        global previous_line
        global previous_filename

        if event == "line":

            filename = os.path.normcase(
                os.path.abspath(
                    frame.f_code.co_filename
                )
            )

            if filename == TARGET_NORMALIZED:

                current_line = (
                    frame.f_lineno
                )

                executed.add(
                    current_line
                )

                if (
                    previous_line is not None
                    and previous_filename
                    == TARGET_NORMALIZED
                ):

                    edge_id = (
                        (previous_line << 32)
                        ^ current_line
                    )

                    edges.add(
                        edge_id
                    )

                previous_line = (
                    current_line
                )

                previous_filename = (
                    TARGET_NORMALIZED
                )

            else:

                previous_line = None

                previous_filename = (
                    filename
                )

        return trace


    output = b""

    status = 0

    try:

        sys.settrace(
            trace
        )

        if target_function is not None:

            result = target_function(
                data
            )

        else:

            result = None

        if result is None:

            output = b""

        elif isinstance(
            result,
            bytes
        ):

            output = result

        else:

            output = str(
                result
            ).encode(
                errors="replace"
            )

    except BaseException as exc:

        status = 1

        output = (
            f"{{type(exc).__name__}}: "
            f"{{exc}}"
        ).encode(
            errors="replace"
        )

        traceback.print_exc(
            file=sys.stderr
        )

    finally:

        sys.settrace(
            None
        )

    coverage_lines = "\\n".join(
        "L:" + str(line)
        for line in sorted(
            executed
        )
    )

    coverage_edges = "\\n".join(
        "E:" + str(edge)
        for edge in sorted(
            edges
        )
    )

    coverage = (
        coverage_lines
        + (
            "\\n"
            if coverage_lines
            and coverage_edges
            else ""
        )
        + coverage_edges
    ).encode()

    # Status is encoded as the first byte
    # of the output payload.
    payload = (
        bytes([status])
        + output
    )

    send(
        sys.stdout.buffer,
        payload
    )

    send(
        sys.stdout.buffer,
        coverage
    )
'''

        worker.write_text(
            source,
            encoding="utf-8"
        )

        return worker

    # =========================================================
    # PERSISTENT EXECUTION
    # =========================================================

    def _run_python_persistent(
        self,
        data: bytes,
        start: float
    ) -> ExecutionResult:
        """
        Execute one input using the persistent worker.
        """

        with self._persistent_lock:

            try:

                self._start_persistent_worker()

                process = (
                    self._persistent_process
                )

                if process is None:

                    raise RuntimeError(
                        "Persistent worker "
                        "could not be started"
                    )

                # -------------------------------------------------
                # SEND INPUT
                # -------------------------------------------------

                process.stdin.write(
                    len(data).to_bytes(
                        4,
                        "little"
                    )
                )

                process.stdin.write(
                    data
                )

                process.stdin.flush()

                # -------------------------------------------------
                # READ RESPONSE
                # -------------------------------------------------

                response = (
                    self._read_exact(
                        process.stdout,
                        4
                    )
                )

                if response is None:

                    raise RuntimeError(
                        "Persistent worker "
                        "closed its output"
                    )

                response_length = int.from_bytes(
                    response,
                    "little"
                )

                payload = (
                    self._read_exact(
                        process.stdout,
                        response_length
                    )
                )

                if payload is None:

                    raise RuntimeError(
                        "Persistent worker "
                        "returned incomplete output"
                    )

                coverage_length_data = (
                    self._read_exact(
                        process.stdout,
                        4
                    )
                )

                if coverage_length_data is None:

                    raise RuntimeError(
                        "Persistent worker "
                        "returned incomplete coverage"
                    )

                coverage_length = (
                    int.from_bytes(
                        coverage_length_data,
                        "little"
                    )
                )

                coverage_data = (
                    self._read_exact(
                        process.stdout,
                        coverage_length
                    )
                )

                if coverage_data is None:

                    raise RuntimeError(
                        "Persistent worker "
                        "returned incomplete coverage"
                    )

                # -------------------------------------------------
                # PARSE RESPONSE
                # -------------------------------------------------

                status_code = (
                    payload[0]
                    if payload
                    else 1
                )

                output = (
                    payload[1:]
                    if payload
                    else b""
                )

                coverage, edges = (
                    self._parse_coverage_bytes(
                        coverage_data
                    )
                )

                bitmap = (
                    self._build_bitmap(
                        edges
                    )
                )

                duration = (
                    time.perf_counter()
                    - start
                )

                if status_code == 0:

                    status = (
                        ExecutionStatus.NORMAL
                    )

                    stderr = b""

                else:

                    status = (
                        ExecutionStatus.CRASH
                    )

                    stderr = output

                return ExecutionResult(
                    status=status,
                    exit_code=(
                        0
                        if status_code == 0
                        else 1
                    ),
                    stdout=(
                        output
                        if status_code == 0
                        else b""
                    ),
                    stderr=stderr,
                    duration=duration,
                    coverage=coverage,
                    bitmap=bitmap,
                    sanitizer=None,
                    sanitizer_message="",
                )

            except TimeoutError:

                self._close_persistent_worker(
                    force=True
                )

                duration = (
                    time.perf_counter()
                    - start
                )

                return ExecutionResult(
                    status=ExecutionStatus.TIMEOUT,
                    exit_code=-1,
                    stdout=b"",
                    stderr=b"",
                    duration=duration,
                    coverage=set(),
                    bitmap=None,
                    sanitizer=None,
                    sanitizer_message="",
                )

            except (
                BrokenPipeError,
                EOFError,
                OSError,
                RuntimeError
            ) as exc:

                self._close_persistent_worker(
                    force=True
                )

                duration = (
                    time.perf_counter()
                    - start
                )

                return ExecutionResult(
                    status=ExecutionStatus.CRASH,
                    exit_code=-1,
                    stdout=b"",
                    stderr=str(exc).encode(
                        errors="replace"
                    ),
                    duration=duration,
                    coverage=set(),
                    bitmap=None,
                    sanitizer=None,
                    sanitizer_message="",
                )

    # =========================================================
    # READ EXACT WITH TIMEOUT
    # =========================================================

    def _read_exact(
        self,
        stream,
        size: int
    ) -> Optional[bytes]:
        """
        Read exactly `size` bytes.

        A daemon thread is used so Windows pipe reads cannot
        block the parent indefinitely.
        """

        result_queue = queue.Queue(
            maxsize=1
        )

        def reader():

            try:

                data = stream.read(
                    size
                )

                result_queue.put(
                    data
                )

            except Exception as exc:

                result_queue.put(
                    exc
                )

        thread = threading.Thread(
            target=reader,
            daemon=True
        )

        thread.start()

        try:

            result = (
                result_queue.get(
                    timeout=self.timeout
                )
            )

        except queue.Empty:

            raise TimeoutError(
                "Persistent worker "
                "response timed out"
            )

        if isinstance(
            result,
            BaseException
        ):

            raise result

        if result is None:

            return None

        if len(result) != size:

            return None

        return result

    # =========================================================
    # PARSE PERSISTENT COVERAGE
    # =========================================================

    def _parse_coverage_bytes(
        self,
        data: bytes
    ) -> tuple[set, set]:
        """
        Parse coverage data emitted by the persistent worker.
        """

        coverage = set()

        edges = set()

        if not data:

            return coverage, edges

        try:

            text = data.decode(
                "utf-8",
                errors="replace"
            )

        except Exception:

            return coverage, edges

        for line in text.splitlines():

            line = line.strip()

            if line.startswith("L:"):

                value = line[2:]

                try:

                    coverage.add(
                        int(value)
                    )

                except ValueError:

                    pass

            elif line.startswith("E:"):

                value = line[2:]

                try:

                    edges.add(
                        int(value)
                    )

                except ValueError:

                    pass

        return coverage, edges

    # =========================================================
    # CLOSE PERSISTENT WORKER
    # =========================================================

    def _close_persistent_worker(
        self,
        force: bool = False
    ):
        """
        Close the persistent worker.
        """

        process = (
            self._persistent_process
        )

        if process is None:

            return

        try:

            if force:

                if process.poll() is None:

                    process.kill()

            else:

                if (
                    self._persistent_stdin
                    is not None
                ):

                    try:

                        self._persistent_stdin.close()

                    except OSError:

                        pass

                process.wait(
                    timeout=1.0
                )

        except (
            OSError,
            subprocess.TimeoutExpired
        ):

            try:

                process.kill()

            except OSError:

                pass

        # -----------------------------------------------------
        # CLOSE STREAMS
        # -----------------------------------------------------

        for stream in (
            self._persistent_stdin,
            self._persistent_stdout,
            self._persistent_stderr,
        ):

            if stream is not None:

                try:

                    stream.close()

                except OSError:

                    pass

        # -----------------------------------------------------
        # DELETE WORKER
        # -----------------------------------------------------

        worker_path = getattr(
            self,
            "_persistent_worker_path",
            None
        )

        if worker_path is not None:

            try:

                worker_path.unlink(
                    missing_ok=True
                )

            except OSError:

                pass

        self._persistent_process = None

        self._persistent_stdin = None

        self._persistent_stdout = None

        self._persistent_stderr = None

        self._persistent_worker_path = None

    # =========================================================
    # PUBLIC CLOSE
    # =========================================================

    def close(self):
        """
        Close resources owned by the executor.
        """

        self._close_persistent_worker(
            force=True
        )

    # =========================================================
    # DESTRUCTOR
    # =========================================================

    def __del__(self):

        try:

            self._close_persistent_worker(
                force=True
            )

        except Exception:

            pass

    # =========================================================
    # SAFE BYTE CONVERSION
    # =========================================================

    @staticmethod
    def _safe_bytes(
        value
    ) -> bytes:
        """
        Safely convert a value to bytes.
        """

        if value is None:

            return b""

        if isinstance(
            value,
            bytes
        ):

            return value

        if isinstance(
            value,
            str
        ):

            return value.encode(
                errors="replace"
            )

        try:

            return bytes(
                value
            )

        except Exception:

            return b""

    # =========================================================
    # STATUS HELPERS
    # =========================================================

    def is_crash(
        self,
        result: ExecutionResult
    ) -> bool:
        """
        Return True when result is a crash.
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
        Return True when result timed out.
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
        Return True when result completed normally.
        """

        return (
            result.status
            == ExecutionStatus.NORMAL
        )


# ============================================================
# MODULE EXPORTS
# ============================================================


__all__ = [
    "ExecutionStatus",
    "ExecutionResult",
    "Executor",
]