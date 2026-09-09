from enum import Enum


class CrashType(Enum):
    """
    Categories of crashes detected by the fuzzer.
    """

    # Python exceptions
    RUNTIME_ERROR = "RuntimeError"
    VALUE_ERROR = "ValueError"
    TYPE_ERROR = "TypeError"
    INDEX_ERROR = "IndexError"
    KEY_ERROR = "KeyError"
    ATTRIBUTE_ERROR = "AttributeError"
    ZERO_DIVISION = "ZeroDivisionError"
    MEMORY_ERROR = "MemoryError"
    ASSERTION_ERROR = "AssertionError"
    SYSTEM_EXIT = "SystemExit"

    # Sanitizer findings
    ASAN_ERROR = "ASanError"
    UBSAN_ERROR = "UBSanError"

    # Native / Windows crashes
    ACCESS_VIOLATION = "AccessViolation"
    STACK_OVERFLOW = "StackOverflow"
    ILLEGAL_INSTRUCTION = "IllegalInstruction"
    INTEGER_DIVIDE_BY_ZERO = "IntegerDivideByZero"
    HEAP_CORRUPTION = "HeapCorruption"

    UNKNOWN = "Unknown"


class CrashClassification:
    """
    Stores the classification of a single crash.
    """

    def __init__(
        self,
        crash_type: CrashType,
        message: str = ""
    ):
        self.crash_type = crash_type
        self.message = message

    @property
    def name(self) -> str:
        """
        Return the human-readable crash type.
        """

        return self.crash_type.value

    def __repr__(self) -> str:
        return (
            f"CrashClassification("
            f"type='{self.name}', "
            f"message={self.message!r}"
            f")"
        )


class CrashClassifier:
    """
    Classifies crashes using information produced by
    target execution.

    Supports:

    - Python exception classification
    - ASan classification
    - UBSan classification
    - stderr-based classification
    - native process exit-code classification
    - Windows structured exception codes
    """

    # =========================================================
    # NATIVE WINDOWS EXIT CODES
    # =========================================================

    NATIVE_EXIT_CODES = {
        # 0xC0000005
        3221225477: CrashType.ACCESS_VIOLATION,

        # 0xC00000FD
        3221225725: CrashType.STACK_OVERFLOW,

        # 0xC000001D
        3221225501: CrashType.ILLEGAL_INSTRUCTION,

        # 0xC0000094
        3221225620: CrashType.INTEGER_DIVIDE_BY_ZERO,

        # 0xC0000374
        3221226356: CrashType.HEAP_CORRUPTION,
    }

    # =========================================================
    # EXCEPTION CLASSIFICATION
    # =========================================================

    def classify_exception(
        self,
        exception: BaseException
    ) -> CrashClassification:
        """
        Classify a Python exception directly.
        """

        exception_type = type(exception)

        mapping = {
            RuntimeError: CrashType.RUNTIME_ERROR,
            ValueError: CrashType.VALUE_ERROR,
            TypeError: CrashType.TYPE_ERROR,
            IndexError: CrashType.INDEX_ERROR,
            KeyError: CrashType.KEY_ERROR,
            AttributeError: CrashType.ATTRIBUTE_ERROR,
            ZeroDivisionError: CrashType.ZERO_DIVISION,
            MemoryError: CrashType.MEMORY_ERROR,
            AssertionError: CrashType.ASSERTION_ERROR,
            SystemExit: CrashType.SYSTEM_EXIT,
        }

        crash_type = mapping.get(
            exception_type,
            CrashType.UNKNOWN
        )

        return CrashClassification(
            crash_type=crash_type,
            message=str(exception)
        )

    # =========================================================
    # SANITIZER CLASSIFICATION
    # =========================================================

    def classify_sanitizer(
        self,
        sanitizer: str | None,
        message: str = ""
    ) -> CrashClassification:
        """
        Classify a sanitizer finding.

        Supported sanitizers:

            asan
            ubsan
        """

        if sanitizer is None:
            return CrashClassification(
                CrashType.UNKNOWN,
                message
            )

        sanitizer_name = str(
            sanitizer
        ).lower().strip()

        if sanitizer_name == "asan":
            return CrashClassification(
                crash_type=CrashType.ASAN_ERROR,
                message=message
            )

        if sanitizer_name == "ubsan":
            return CrashClassification(
                crash_type=CrashType.UBSAN_ERROR,
                message=message
            )

        return CrashClassification(
            crash_type=CrashType.UNKNOWN,
            message=message
        )

    # =========================================================
    # NATIVE EXIT-CODE CLASSIFICATION
    # =========================================================

    def classify_exit_code(
        self,
        exit_code: int | None
    ) -> CrashClassification:
        """
        Classify a native crash using its process exit code.

        Windows native crashes are commonly represented as
        NTSTATUS exception codes encoded as process exit codes.
        """

        if exit_code is None:
            return CrashClassification(
                CrashType.UNKNOWN,
                ""
            )

        crash_type = self.NATIVE_EXIT_CODES.get(
            exit_code
        )

        if crash_type is None:
            return CrashClassification(
                CrashType.UNKNOWN,
                f"Native process exited with code "
                f"{exit_code}"
            )

        hex_code = (
            f"0x{exit_code & 0xFFFFFFFF:08X}"
        )

        return CrashClassification(
            crash_type=crash_type,
            message=(
                f"Native process terminated with "
                f"Windows exception code {hex_code}"
            )
        )

    # =========================================================
    # STDERR CLASSIFICATION
    # =========================================================

    def classify_stderr(
        self,
        stderr: bytes | str
    ) -> CrashClassification:
        """
        Classify a crash using stderr generated by
        a subprocess execution.
        """

        if isinstance(stderr, bytes):
            text = stderr.decode(
                "utf-8",
                errors="replace"
            )
        else:
            text = str(stderr)

        text = text.strip()

        if not text:
            return CrashClassification(
                CrashType.UNKNOWN
            )

        # -----------------------------------------------------
        # ASan
        # -----------------------------------------------------

        if "AddressSanitizer:" in text:

            return CrashClassification(
                crash_type=CrashType.ASAN_ERROR,
                message=text
            )

        # -----------------------------------------------------
        # UBSan
        # -----------------------------------------------------

        if (
            "UndefinedBehaviorSanitizer:"
            in text
        ):

            return CrashClassification(
                crash_type=CrashType.UBSAN_ERROR,
                message=text
            )

        # -----------------------------------------------------
        # Python exception names
        # -----------------------------------------------------

        exception_map = {
            "RuntimeError": CrashType.RUNTIME_ERROR,
            "ValueError": CrashType.VALUE_ERROR,
            "TypeError": CrashType.TYPE_ERROR,
            "IndexError": CrashType.INDEX_ERROR,
            "KeyError": CrashType.KEY_ERROR,
            "AttributeError": CrashType.ATTRIBUTE_ERROR,
            "ZeroDivisionError": CrashType.ZERO_DIVISION,
            "MemoryError": CrashType.MEMORY_ERROR,
            "AssertionError": CrashType.ASSERTION_ERROR,
            "SystemExit": CrashType.SYSTEM_EXIT,
        }

        for exception_name, crash_type in (
            exception_map.items()
        ):

            if exception_name in text:

                message = self._extract_message(
                    text,
                    exception_name
                )

                return CrashClassification(
                    crash_type=crash_type,
                    message=message
                )

        # -----------------------------------------------------
        # Native crash keywords
        # -----------------------------------------------------

        native_patterns = {
            "access violation":
                CrashType.ACCESS_VIOLATION,

            "segmentation fault":
                CrashType.ACCESS_VIOLATION,

            "stack overflow":
                CrashType.STACK_OVERFLOW,

            "illegal instruction":
                CrashType.ILLEGAL_INSTRUCTION,

            "integer divide by zero":
                CrashType.INTEGER_DIVIDE_BY_ZERO,

            "heap corruption":
                CrashType.HEAP_CORRUPTION,
        }

        lowered = text.lower()

        for pattern, crash_type in (
            native_patterns.items()
        ):

            if pattern in lowered:

                return CrashClassification(
                    crash_type=crash_type,
                    message=text
                )

        return CrashClassification(
            crash_type=CrashType.UNKNOWN,
            message=text
        )

    # =========================================================
    # EXECUTION RESULT CLASSIFICATION
    # =========================================================

    def classify(
        self,
        result
    ) -> CrashClassification:
        """
        Classify an ExecutionResult.

        Classification order:

        1. Explicit sanitizer information
        2. Known stderr information
        3. Native process exit code
        4. Unknown crash
        """

        sanitizer = getattr(
            result,
            "sanitizer",
            None
        )

        sanitizer_message = getattr(
            result,
            "sanitizer_message",
            ""
        )

        stderr = getattr(
            result,
            "stderr",
            b""
        )

        exit_code = getattr(
            result,
            "exit_code",
            None
        )

        # -----------------------------------------------------
        # Explicit sanitizer information
        # -----------------------------------------------------

        if sanitizer is not None:

            sanitizer_classification = (
                self.classify_sanitizer(
                    sanitizer,
                    sanitizer_message
                )
            )

            if self.is_known(
                sanitizer_classification
            ):
                return sanitizer_classification

        # -----------------------------------------------------
        # Try stderr
        # -----------------------------------------------------

        stderr_classification = (
            self.classify_stderr(stderr)
        )

        if self.is_known(
            stderr_classification
        ):
            return stderr_classification

        # -----------------------------------------------------
        # Try native exit code
        # -----------------------------------------------------

        native_classification = (
            self.classify_exit_code(
                exit_code
            )
        )

        if self.is_known(
            native_classification
        ):
            return native_classification

        # -----------------------------------------------------
        # Preserve stderr if available
        # -----------------------------------------------------

        if stderr_classification.message:
            return stderr_classification

        return native_classification

    # =========================================================
    # MESSAGE EXTRACTION
    # =========================================================

    def _extract_message(
        self,
        text: str,
        exception_name: str
    ) -> str:
        """
        Extract the message following the exception name.

        Example:

            RuntimeError: Intentional fuzzing crash

        becomes:

            Intentional fuzzing crash
        """

        for line in reversed(
            text.splitlines()
        ):

            line = line.strip()

            if exception_name in line:

                parts = line.split(
                    exception_name,
                    1
                )

                if len(parts) == 2:

                    message = (
                        parts[1]
                        .lstrip(": ")
                        .strip()
                    )

                    if message:
                        return message

        return ""

    # =========================================================
    # CONVENIENCE HELPERS
    # =========================================================

    def is_known(
        self,
        classification: CrashClassification
    ) -> bool:
        """
        Return True if the crash was assigned a
        known crash category.
        """

        return (
            classification.crash_type
            != CrashType.UNKNOWN
        )

    def get_type(
        self,
        classification: CrashClassification
    ) -> str:
        """
        Return the human-readable crash type.
        """

        return classification.name

    def get_message(
        self,
        classification: CrashClassification
    ) -> str:
        """
        Return the extracted crash message.
        """

        return classification.message