import sys


class CoverageTracker:
    """
    Tracks line and edge coverage for the target program.

    Line coverage:
        Stores individual executed line numbers.

    Edge coverage:
        Stores transitions between consecutive executed lines.
        Each edge is represented by a deterministic integer ID.
    """

    def __init__(self):
        self.lines = set()
        self.edges = set()

        self.enabled = False
        self.previous_line = None

    # =========================================================
    # TRACE
    # =========================================================

    def trace(self, frame, event, arg):

        if not self.enabled:
            return self.trace

        if event == "line":

            filename = frame.f_code.co_filename

            if filename.endswith("target.py"):

                current_line = frame.f_lineno

                # -------------------------------------------------
                # LINE COVERAGE
                # -------------------------------------------------

                self.lines.add(current_line)

                # -------------------------------------------------
                # EDGE COVERAGE
                # -------------------------------------------------

                if self.previous_line is not None:

                    edge_id = (
                        self.previous_line << 32
                    ) ^ current_line

                    self.edges.add(edge_id)

                self.previous_line = current_line

        return self.trace

    # =========================================================
    # START
    # =========================================================

    def start(self):

        self.lines.clear()
        self.edges.clear()

        self.previous_line = None
        self.enabled = True

        sys.settrace(self.trace)

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        sys.settrace(None)

        self.enabled = False
        self.previous_line = None

    # =========================================================
    # LINE COVERAGE
    # =========================================================

    def get_coverage(self):

        return sorted(self.lines)

    def get_signature(self):

        return ",".join(
            str(line)
            for line in sorted(self.lines)
        )

    def has_line(self, line_number):

        return line_number in self.lines

    def coverage_count(self):

        return len(self.lines)

    # =========================================================
    # EDGE COVERAGE
    # =========================================================

    def get_edges(self):

        """
        Return all discovered edge IDs.
        """

        return set(self.edges)

    def edge_count(self):

        """
        Return the number of unique discovered edges.
        """

        return len(self.edges)

    def has_edge(self, edge_id):

        """
        Return True if an edge has been observed.
        """

        return edge_id in self.edges

    def get_edge_signature(self):

        """
        Return a deterministic representation of
        the discovered edges.
        """

        return ",".join(
            str(edge)
            for edge in sorted(self.edges)
        )

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        self.lines.clear()
        self.edges.clear()

        self.previous_line = None

    # =========================================================
    # MERGE
    # =========================================================

    def merge(self, coverage):

        before = len(self.lines)

        self.lines.update(coverage)

        return len(self.lines) > before

    # =========================================================
    # EDGE MERGE
    # =========================================================

    def merge_edges(self, edges):

        before = len(self.edges)

        self.edges.update(edges)

        return len(self.edges) > before

    # =========================================================
    # NEW LINE COVERAGE
    # =========================================================

    def is_new_coverage(self, coverage):

        return bool(
            set(coverage) - self.lines
        )

    def get_new_coverage(self, coverage):

        return set(coverage) - self.lines

    # =========================================================
    # LENGTH
    # =========================================================

    def __len__(self):

        return len(self.lines)

    # =========================================================
    # CONTAINS
    # =========================================================

    def __contains__(self, line_number):

        return line_number in self.lines

    # =========================================================
    # REPRESENTATION
    # =========================================================

    def __repr__(self):

        return (
            "CoverageTracker("
            f"lines={len(self.lines)}, "
            f"edges={len(self.edges)}, "
            f"enabled={self.enabled}"
            ")"
        )