from dataclasses import dataclass
from enum import Enum


class SanitizationStatus(Enum):
    """
    Result of sanitizing a fuzzing input.
    """

    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class SanitizationResult:
    """
    Stores the result of input sanitization.
    """

    status: SanitizationStatus
    data: bytes
    reason: str = ""

    @property
    def accepted(self) -> bool:
        """
        Return True when the input is safe to execute.
        """

        return (
            self.status
            == SanitizationStatus.ACCEPTED
        )


class Sanitizer:
    """
    Input sanitization layer for the fuzzing pipeline.

    The sanitizer protects the fuzzing infrastructure from
    invalid input types and excessively large inputs while
    preserving malformed byte sequences that may be useful
    for discovering target vulnerabilities.

    It does NOT attempt to make the target input semantically
    valid.
    """

    def __init__(
        self,
        max_input_size: int = 4096
    ):
        if max_input_size <= 0:
            raise ValueError(
                "max_input_size must be greater than 0"
            )

        self.max_input_size = max_input_size

    # =========================================================
    # MAIN SANITIZATION
    # =========================================================

    def sanitize(
        self,
        data: bytes
    ) -> SanitizationResult:
        """
        Validate and sanitize one fuzzing input.

        Returns a SanitizationResult describing whether
        the input should be executed.
        """

        # -----------------------------------------------------
        # TYPE VALIDATION
        # -----------------------------------------------------

        if not isinstance(data, bytes):

            return SanitizationResult(
                status=SanitizationStatus.REJECTED,
                data=b"",
                reason="Input must be bytes.",
            )

        # -----------------------------------------------------
        # SIZE VALIDATION
        # -----------------------------------------------------

        if len(data) > self.max_input_size:

            return SanitizationResult(
                status=SanitizationStatus.REJECTED,
                data=b"",
                reason=(
                    f"Input exceeds maximum size of "
                    f"{self.max_input_size} bytes."
                ),
            )

        # -----------------------------------------------------
        # ACCEPT INPUT
        # -----------------------------------------------------

        return SanitizationResult(
            status=SanitizationStatus.ACCEPTED,
            data=data,
        )

    # =========================================================
    # CONVENIENCE METHOD
    # =========================================================

    def is_safe(
        self,
        data: bytes
    ) -> bool:
        """
        Return True if the input passes sanitization.
        """

        return self.sanitize(data).accepted