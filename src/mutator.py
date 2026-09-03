import random


class Mutator:
    """
    Byte-level mutation engine used by the coverage-guided fuzzer.

    Supported mutations:
        - flip_bit()
        - flip_byte()
        - insert_byte()
        - delete_byte()
        - replace_byte()
        - arithmetic_mutation()
        - mutate()
        - mutate_n()
        - random_mutation()
    """

    def __init__(self, max_size: int = 4096):
        if max_size < 1:
            raise ValueError("max_size must be at least 1")

        self.max_size = max_size

    # =========================================================
    # FLIP BIT
    # =========================================================

    def flip_bit(self, data: bytes) -> bytes:
        """
        Flip one random bit.

        Input length remains unchanged.
        """

        if not data:
            return data

        result = bytearray(data)

        index = random.randrange(len(result))
        bit = 1 << random.randrange(8)

        result[index] ^= bit

        return bytes(result)

    # =========================================================
    # FLIP BYTE
    # =========================================================

    def flip_byte(self, data: bytes) -> bytes:
        """
        Invert all bits in one random byte.

        Input length remains unchanged.
        """

        if not data:
            return data

        result = bytearray(data)

        index = random.randrange(len(result))

        result[index] ^= 0xFF

        return bytes(result)

    # =========================================================
    # INSERT BYTE
    # =========================================================

    def insert_byte(self, data: bytes) -> bytes:
        """
        Insert one random byte.

        Does not exceed max_size.
        """

        if len(data) >= self.max_size:
            return data

        result = bytearray(data)

        position = random.randrange(len(result) + 1)
        value = random.randrange(256)

        result.insert(position, value)

        return bytes(result)

    # =========================================================
    # DELETE BYTE
    # =========================================================

    def delete_byte(self, data: bytes) -> bytes:
        """
        Delete one random byte.

        Empty input remains unchanged.
        """

        if not data:
            return data

        result = bytearray(data)

        position = random.randrange(len(result))

        del result[position]

        return bytes(result)

    # =========================================================
    # REPLACE BYTE
    # =========================================================

    def replace_byte(self, data: bytes) -> bytes:
        """
        Replace one random byte with another byte.

        Input length remains unchanged.
        """

        if not data:
            return data

        result = bytearray(data)

        position = random.randrange(len(result))
        original = result[position]

        replacement = random.randrange(256)

        while replacement == original:
            replacement = random.randrange(256)

        result[position] = replacement

        return bytes(result)

    # =========================================================
    # ARITHMETIC MUTATION
    # =========================================================

    def arithmetic_mutation(self, data: bytes) -> bytes:
        """
        Add or subtract a small value from one byte.

        Input length remains unchanged.
        """

        if not data:
            return data

        result = bytearray(data)

        position = random.randrange(len(result))

        delta = random.choice(
            [
                -35,
                -16,
                -8,
                -4,
                -2,
                -1,
                1,
                2,
                4,
                8,
                16,
                35,
            ]
        )

        result[position] = (
            result[position] + delta
        ) % 256

        return bytes(result)

    # =========================================================
    # MUTATE
    # =========================================================

    def mutate(self, data: bytes) -> bytes:
        """
        Perform one random mutation.

        Empty input is handled separately because
        deletion/replacement/bit flipping cannot
        modify an empty byte string.
        """

        if not data:
            return self.insert_byte(data)

        mutation = random.choice(
            [
                self.flip_bit,
                self.flip_byte,
                self.insert_byte,
                self.delete_byte,
                self.replace_byte,
                self.arithmetic_mutation,
            ]
        )

        return mutation(data)

    # =========================================================
    # MUTATE N
    # =========================================================

    def mutate_n(
        self,
        data: bytes,
        count: int = 1
    ) -> bytes:
        """
        Apply mutation repeatedly.

        Returns one bytes object.

        count=0:
            returns original input.

        count=1:
            performs one mutation.

        count>1:
            performs multiple sequential mutations.
        """

        if count < 0:
            raise ValueError(
                "count must be non-negative"
            )

        result = data

        for _ in range(count):
            result = self.mutate(result)

        return result

    # =========================================================
    # RANDOM MUTATION
    # =========================================================

    def random_mutation(self, data: bytes) -> bytes:
        """
        Compatibility wrapper around mutate().
        """

        return self.mutate(data)