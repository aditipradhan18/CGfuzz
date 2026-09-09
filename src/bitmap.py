class CoverageBitmap:
    """
    Fixed-size bitmap used to represent coverage.

    Each edge is mapped to one slot in the bitmap.
    """

    def __init__(self, size=65536):

        if size <= 0:
            raise ValueError(
                "Bitmap size must be positive"
            )

        self.size = size
        self.bitmap = bytearray(size)

    def index(self, edge_id):

        return edge_id % self.size

    def record(self, edge_id):

        index = self.index(edge_id)

        was_new = self.bitmap[index] == 0

        if self.bitmap[index] < 255:
            self.bitmap[index] += 1

        return was_new

    def has_edge(self, edge_id):

        return (
            self.bitmap[self.index(edge_id)] != 0
        )

    def hit_count(self):

        return sum(
            1
            for value in self.bitmap
            if value != 0
        )

    def get_bitmap(self):

        return bytes(self.bitmap)

    def reset(self):

        self.bitmap = bytearray(self.size)

    def merge(self, other):

        if not isinstance(
            other,
            CoverageBitmap
        ):
            raise TypeError(
                "other must be a CoverageBitmap"
            )

        if other.size != self.size:
            raise ValueError(
                "Bitmap sizes must match"
            )

        new_coverage = False

        for i in range(self.size):

            if other.bitmap[i] != 0:

                if self.bitmap[i] == 0:
                    new_coverage = True

                if other.bitmap[i] > self.bitmap[i]:
                    self.bitmap[i] = other.bitmap[i]

        return new_coverage

    def copy(self):

        result = CoverageBitmap(self.size)

        result.bitmap[:] = self.bitmap

        return result

    def __len__(self):

        return self.size

    def __repr__(self):

        return (
            "CoverageBitmap("
            f"size={self.size}, "
            f"hits={self.hit_count()}"
            ")"
        )