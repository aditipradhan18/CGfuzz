import hashlib
import json
from pathlib import Path


class CrashDatabase:
    """
    Persistent crash database.

    Stores discovered crashes and prevents duplicate
    crash signatures from being saved multiple times.
    """

    def __init__(self, directory="crashes"):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True
        )

        self.hashes_file = (
            self.directory / "crash_hashes.txt"
        )

        self.crash_hashes = set()

        self._load_hashes()

    # =========================================================
    # LOAD HASHES
    # =========================================================

    def _load_hashes(self):
        """
        Load previously stored crash hashes.
        """

        if not self.hashes_file.exists():
            return

        try:
            with self.hashes_file.open(
                "r",
                encoding="utf-8"
            ) as file:

                for line in file:
                    value = line.strip()

                    if value:
                        self.crash_hashes.add(value)

        except OSError:
            return

    # =========================================================
    # HASH
    # =========================================================

    def get_hash(self, signature: str) -> str:
        """
        Generate a stable SHA-256 hash for a crash signature.

        The first 16 hexadecimal characters are used as the
        crash identifier.
        """

        return hashlib.sha256(
            signature.encode("utf-8")
        ).hexdigest()[:16]

    # =========================================================
    # DUPLICATE CHECK
    # =========================================================

    def is_duplicate(
        self,
        signature: str
    ) -> bool:
        """
        Return True if this crash signature has already
        been recorded.
        """

        crash_hash = self.get_hash(signature)

        return crash_hash in self.crash_hashes

    # =========================================================
    # ADD CRASH
    # =========================================================

    def add_crash(
        self,
        signature: str,
        input_data: bytes,
        metadata=None
    ) -> bool:
        """
        Store a crash if it has not already been seen.

        Returns:

            True  -> new crash stored
            False -> duplicate or storage failure
        """

        if not isinstance(input_data, bytes):
            input_data = bytes(input_data)

        crash_hash = self.get_hash(signature)

        # -----------------------------------------------------
        # DEDUPLICATION
        # -----------------------------------------------------

        if crash_hash in self.crash_hashes:
            return False

        binary_file = (
            self.directory /
            f"crash_{crash_hash}.bin"
        )

        metadata_file = (
            self.directory /
            f"crash_{crash_hash}.txt"
        )

        # -----------------------------------------------------
        # SAVE BINARY
        # -----------------------------------------------------

        try:
            binary_file.write_bytes(
                input_data
            )

        except OSError:
            return False

        # -----------------------------------------------------
        # SAVE METADATA
        # -----------------------------------------------------

        record = {
            "hash": crash_hash,
            "signature": signature,
            "size": len(input_data),
            "metadata": metadata or {}
        }

        try:
            metadata_file.write_text(
                json.dumps(
                    record,
                    indent=4
                ),
                encoding="utf-8"
            )

        except OSError:

            # Remove binary if metadata storage failed.
            try:
                binary_file.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

            return False

        # -----------------------------------------------------
        # PERSIST HASH
        # -----------------------------------------------------

        try:
            with self.hashes_file.open(
                "a",
                encoding="utf-8"
            ) as file:

                file.write(
                    crash_hash + "\n"
                )

        except OSError:

            # Roll back files if hash persistence failed.
            try:
                binary_file.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

            try:
                metadata_file.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

            return False

        # -----------------------------------------------------
        # REGISTER IN MEMORY
        # -----------------------------------------------------

        self.crash_hashes.add(
            crash_hash
        )

        return True

    # =========================================================
    # GET CRASHES
    # =========================================================

    def get_crashes(self):
        """
        Return all known crash hashes in sorted order.
        """

        return sorted(
            self.crash_hashes
        )

    # =========================================================
    # COUNT
    # =========================================================

    def count(self) -> int:
        """
        Return the number of unique crashes.
        """

        return len(
            self.crash_hashes
        )

    # =========================================================
    # LENGTH
    # =========================================================

    def __len__(self):
        """
        Allow:

            len(database)
        """

        return len(
            self.crash_hashes
        )

    # =========================================================
    # CONTAINS
    # =========================================================

    def __contains__(
        self,
        signature: str
    ):
        """
        Allow:

            signature in database
        """

        return self.is_duplicate(
            signature
        )

    # =========================================================
    # REPRESENTATION
    # =========================================================

    def __repr__(self):
        return (
            f"CrashDatabase("
            f"crashes={len(self.crash_hashes)}, "
            f"directory='{self.directory}'"
            f")"
        )