import sys


class CoverageTracker:
    """
    Tracks line coverage for the target program.

    Coverage is represented as a set of line numbers.
    """

    def __init__(self):
        self.lines = set()
        self.enabled = False

    # =============================================================
    # TRACE
    # =============================================================

    def trace(self, frame, event, arg):
        """
        Trace execution events and record target.py line numbers.
        """

        if not self.enabled:
            return self.trace

        if event == "line":

            filename = frame.f_code.co_filename

            if filename.endswith("target.py"):
                self.lines.add(
                    frame.f_lineno
                )

        return self.trace

    # =============================================================
    # START
    # =============================================================

    def start(self):
        """
        Start collecting coverage.
        """

        self.lines.clear()

        self.enabled = True

        sys.settrace(
            self.trace
        )

    # =============================================================
    # STOP
    # =============================================================

    def stop(self):
        """
        Stop collecting coverage.
        """

        sys.settrace(None)

        self.enabled = False

    # =============================================================
    # GET COVERAGE
    # =============================================================

    def get_coverage(self):
        """
        Return covered line numbers in sorted order.
        """

        return sorted(
            self.lines
        )

    # =============================================================
    # COVERAGE SIGNATURE
    # =============================================================

    def get_signature(self):
        """
        Return a deterministic coverage signature.

        Example:

            10,11,12,15
        """

        return ",".join(
            str(line)
            for line in sorted(self.lines)
        )

    # =============================================================
    # LINE CHECK
    # =============================================================

    def has_line(self, line_number):
        """
        Check whether a specific target line was executed.
        """

        return line_number in self.lines

    # =============================================================
    # COVERAGE COUNT
    # =============================================================

    def coverage_count(self):
        """
        Return the number of unique covered lines.
        """

        return len(self.lines)

    # =============================================================
    # RESET
    # =============================================================

    def reset(self):
        """
        Clear all recorded coverage.
        """

        self.lines.clear()

    # =============================================================
    # MERGE
    # =============================================================

    def merge(self, coverage):
        """
        Merge another coverage collection into this tracker.

        Returns True if new lines were discovered.
        """

        before = len(self.lines)

        self.lines.update(
            coverage
        )

        return len(self.lines) > before

    # =============================================================
    # NEW COVERAGE CHECK
    # =============================================================

    def is_new_coverage(self, coverage):
        """
        Check whether the supplied coverage contains
        at least one line not already recorded.
        """

        return bool(
            set(coverage) - self.lines
        )

    # =============================================================
    # GET NEW COVERAGE
    # =============================================================

    def get_new_coverage(self, coverage):
        """
        Return only the coverage lines that are new.
        """

        return (
            set(coverage)
            - self.lines
        )

    # =============================================================
    # LENGTH
    # =============================================================

    def __len__(self):
        """
        Return the number of covered lines.
        """

        return len(self.lines)

    # =============================================================
    # CONTAINS
    # =============================================================

    def __contains__(self, line_number):
        """
        Allow:

            line_number in tracker
        """

        return line_number in self.lines

    # =============================================================
    # REPRESENTATION
    # =============================================================

    def __repr__(self):
        return (
            f"CoverageTracker("
            f"lines={len(self.lines)}, "
            f"enabled={self.enabled}"
            f")"
        )