from __future__ import annotations

from dataclasses import dataclass

from .executor import ExecutionResult, ExecutionStatus


@dataclass
class ReproductionResult:
    reproduced: bool
    attempts: int
    crashes: int
    normal: int
    timeouts: int


class CrashReproducer:
    """
    Re-run an input multiple times and determine whether
    the original crash is reproducible.
    """

    def __init__(self, executor, attempts: int = 3):
        if attempts < 1:
            raise ValueError(
                "attempts must be greater than or equal to 1"
            )

        self.executor = executor
        self.attempts = attempts

    @staticmethod
    def _is_timeout(result: ExecutionResult) -> bool:
        """
        Detect timeout results.

        Normally the executor reports ExecutionStatus.TIMEOUT.
        Some test doubles/targets may expose the timeout through
        stdout or stderr using the TIMEOUT marker.
        """

        if result.status == ExecutionStatus.TIMEOUT:
            return True

        stdout = result.stdout or b""
        stderr = result.stderr or b""

        if isinstance(stdout, str):
            stdout = stdout.encode(errors="replace")

        if isinstance(stderr, str):
            stderr = stderr.encode(errors="replace")

        timeout_markers = (
            b"TIMEOUT",
            b"Timeout",
            b"timeout",
        )

        return any(
            marker in stdout or marker in stderr
            for marker in timeout_markers
        )

    def reproduce(self, data: bytes) -> ReproductionResult:
        """
        Execute the input repeatedly.

        Timeouts are counted separately and are never treated
        as reproducible crashes.
        """

        crashes = 0
        normal = 0
        timeouts = 0

        for _ in range(self.attempts):
            result: ExecutionResult = self.executor.run(data)

            if self._is_timeout(result):
                timeouts += 1

            elif result.status == ExecutionStatus.CRASH:
                crashes += 1

            elif result.status == ExecutionStatus.NORMAL:
                normal += 1

        return ReproductionResult(
            reproduced=crashes > 0,
            attempts=self.attempts,
            crashes=crashes,
            normal=normal,
            timeouts=timeouts,
        )

    def is_reproducible(self, data: bytes) -> bool:
        """
        Return True only when the input produces an actual crash.
        """

        result = self.reproduce(data)
        return result.reproduced

    def verify(self, data: bytes) -> bool:
        """
        Alias for is_reproducible().
        """

        return self.is_reproducible(data)