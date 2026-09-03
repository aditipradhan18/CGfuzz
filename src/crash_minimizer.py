from src.executor import Executor, ExecutionStatus


class CrashMinimizer:
    """
    Minimizes crashing inputs.

    The minimizer repeatedly removes portions of the input
    while checking whether the target still crashes.

    If the reduced input still causes a crash, the reduction
    is kept.
    """

    def __init__(
        self,
        executor: Executor
    ):
        self.executor = executor

    # =========================================================
    # MAIN MINIMIZATION FUNCTION
    # =========================================================

    def minimize(
        self,
        crashing_input: bytes
    ) -> bytes:
        """
        Return the smallest input that still crashes.

        Uses a simple byte-deletion strategy.
        """

        if not isinstance(crashing_input, bytes):
            crashing_input = bytes(crashing_input)

        # -----------------------------------------------------
        # Verify that the original input actually crashes.
        # -----------------------------------------------------

        original_result = self.executor.run(
            crashing_input
        )

        if original_result.status != ExecutionStatus.CRASH:
            return crashing_input

        current = crashing_input

        # -----------------------------------------------------
        # Try removing each byte.
        # -----------------------------------------------------

        changed = True

        while changed:

            changed = False

            index = 0

            while index < len(current):

                candidate = (
                    current[:index]
                    + current[index + 1:]
                )

                result = self.executor.run(
                    candidate
                )

                if result.status == ExecutionStatus.CRASH:

                    current = candidate
                    changed = True

                    # Do not increment index because the
                    # current position now contains the next byte.
                    continue

                index += 1

        return current

    # =========================================================
    # ALIAS
    # =========================================================

    def reduce(
        self,
        crashing_input: bytes
    ) -> bytes:
        """
        Alias for minimize().
        """

        return self.minimize(crashing_input)