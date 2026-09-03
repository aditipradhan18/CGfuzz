from dataclasses import dataclass

from src.executor import Executor, ExecutionStatus


@dataclass
class ReproductionResult:
    """
    Stores the result of attempting to reproduce a crash.
    """

    reproduced: bool
    attempts: int
    crashes: int
    normal: int
    timeouts: int

    def __repr__(self) -> str:
        return (
            "ReproductionResult("
            f"reproduced={self.reproduced}, "
            f"attempts={self.attempts}, "
            f"crashes={self.crashes}, "
            f"normal={self.normal}, "
            f"timeouts={self.timeouts}"
            ")"
        )


class CrashReproducer:
    """
    Verifies whether a crashing input can be reproduced.

    The same input is executed multiple times so that
    unstable or non-deterministic crashes can be identified.
    """

    def __init__(
        self,
        executor: Executor,
        attempts: int = 3
    ):
        if attempts < 1:
            raise ValueError(
                "attempts must be at least 1"
            )

        self.executor = executor
        self.attempts = attempts

    # =========================================================
    # REPRODUCE
    # =========================================================

    def reproduce(
        self,
        data: bytes
    ) -> ReproductionResult:
        """
        Execute the crashing input multiple times.

        A crash is considered reproduced if at least one
        execution results in ExecutionStatus.CRASH.
        """

        if not isinstance(data, bytes):
            data = bytes(data)

        crashes = 0
        normal = 0
        timeouts = 0

        for _ in range(self.attempts):

            result = self.executor.run(data)

            if result.status == ExecutionStatus.CRASH:
                crashes += 1

            elif result.status == ExecutionStatus.TIMEOUT:
                timeouts += 1

            else:
                normal += 1

        return ReproductionResult(
            reproduced=crashes > 0,
            attempts=self.attempts,
            crashes=crashes,
            normal=normal,
            timeouts=timeouts,
        )

    # =========================================================
    # STRICT REPRODUCTION
    # =========================================================

    def is_reproducible(
        self,
        data: bytes
    ) -> bool:
        """
        Return True only if every reproduction attempt
        results in a crash.

        This is useful for detecting stable crashes.
        """

        result = self.reproduce(data)

        return (
            result.crashes == result.attempts
        )

    # =========================================================
    # SINGLE CHECK
    # =========================================================

    def verify(
        self,
        data: bytes
    ) -> bool:
        """
        Perform a single execution and return whether
        the input still crashes.
        """

        if not isinstance(data, bytes):
            data = bytes(data)

        result = self.executor.run(data)

        return (
            result.status
            == ExecutionStatus.CRASH
        )