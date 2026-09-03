import sys


def process(data: bytes) -> str:
    """
    Target program used by the fuzzer.

    Different inputs exercise different execution paths.
    Specific malformed inputs intentionally trigger crashes
    so the fuzzer can detect, minimize, and store them.
    """

    # Empty input
    if not data:
        return "EMPTY"

    # ---------------------------------------------------------
    # Basic paths
    # ---------------------------------------------------------

    if data.startswith(b"A"):

        if len(data) > 1 and data[1:2] == b"B":
            return "PATH_AB"

        return "PATH_A"

    if data.startswith(b"B"):

        if len(data) > 1 and data[1:2] == b"C":
            return "PATH_BC"

        return "PATH_B"

    # ---------------------------------------------------------
    # CRASH CONDITIONS
    # ---------------------------------------------------------

    # Exact crash trigger
    if data == b"CRASH":
        raise RuntimeError(
            "Intentional fuzzing crash"
        )

    # Crash when the input contains a specific sequence
    if b"CRASH" in data:
        raise RuntimeError(
            "Crash sequence detected"
        )

    # ---------------------------------------------------------
    # Additional execution paths
    # ---------------------------------------------------------

    if data.startswith(b"FUZZ"):

        if len(data) >= 5:

            if data[4:5] == b"1":
                return "FUZZ_LEVEL_1"

            if data[4:5] == b"2":
                return "FUZZ_LEVEL_2"

            if data[4:5] == b"3":
                return "FUZZ_LEVEL_3"

        return "FUZZ"

    if b"TEST" in data:
        return "TEST_PATH"

    if b"HELLO" in data:
        return "HELLO_PATH"

    # ---------------------------------------------------------
    # Length-based paths
    # ---------------------------------------------------------

    if len(data) == 1:
        return "LENGTH_1"

    if len(data) < 4:
        return "SHORT_INPUT"

    if len(data) < 8:
        return "MEDIUM_INPUT"

    if len(data) >= 8:
        return "LONG_INPUT"

    return "NORMAL"


def main():
    """
    Read fuzzing input from stdin and process it.
    """

    data = sys.stdin.buffer.read()

    result = process(data)

    print(result)


if __name__ == "__main__":
    main()


# Compatibility alias for the fuzzer
target = process