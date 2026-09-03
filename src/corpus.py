import json
import random
from pathlib import Path


class Corpus:
    """
    Coverage-guided persistent corpus manager.

    Stores interesting inputs on disk together with the
    coverage discovered by each input.
    """

    def __init__(self, directory="corpus"):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True
        )

        self.metadata_file = (
            self.directory / "metadata.json"
        )

        # Stored inputs
        self.inputs = []

        # Coverage associated with each input
        self.coverage = []

        # Load existing corpus from disk
        self._load()

    # =========================================================
    # ADD INPUT
    # =========================================================

    def add(self, data: bytes, coverage=None):
        """
        Add a new input to the corpus.

        Duplicate inputs are ignored.

        Returns:
            True  -> input was added
            False -> input already exists
        """

        if not isinstance(data, bytes):
            data = bytes(data)

        # Avoid duplicates
        if data in self.inputs:
            return False

        if coverage is None:
            coverage = set()

        coverage = set(coverage)

        self.inputs.append(data)
        self.coverage.append(coverage)

        # Persist immediately
        self._save()

        return True

    # =========================================================
    # COMPATIBILITY METHOD
    # =========================================================

    def add_input(self, data: bytes, coverage=None):
        """
        Alias for add().
        """

        return self.add(
            data,
            coverage
        )

    # =========================================================
    # RANDOM INPUT
    # =========================================================

    def random(self):
        """
        Select a corpus input.

        Inputs with greater coverage receive a
        higher probability of being selected.
        """

        if not self.inputs:
            raise IndexError(
                "Corpus is empty"
            )

        weights = []

        for coverage in self.coverage:

            # Base weight prevents zero probability
            weight = 1 + len(coverage)

            weights.append(weight)

        return random.choices(
            self.inputs,
            weights=weights,
            k=1
        )[0]

    # =========================================================
    # COMPATIBILITY METHOD
    # =========================================================

    def random_input(self):
        """
        Alias for random().
        """

        return self.random()

    # =========================================================
    # GET COVERAGE
    # =========================================================

    def get_coverage(self, data: bytes):
        """
        Return the coverage associated with an input.

        Returns an empty set if the input does not exist.
        """

        try:

            index = self.inputs.index(data)

            return set(
                self.coverage[index]
            )

        except ValueError:

            return set()

    # =========================================================
    # UPDATE COVERAGE
    # =========================================================

    def update_coverage(
        self,
        data: bytes,
        coverage
    ):
        """
        Update coverage associated with an existing input.

        Returns True if new coverage was discovered.
        Returns False otherwise.
        """

        try:

            index = self.inputs.index(data)

        except ValueError:

            return False

        coverage = set(coverage)

        old_coverage = self.coverage[index]

        new_coverage = (
            coverage -
            old_coverage
        )

        if new_coverage:

            old_coverage.update(
                new_coverage
            )

            # Persist updated coverage
            self._save()

            return True

        return False

    # =========================================================
    # GET ALL INPUTS
    # =========================================================

    def get_all(self):
        """
        Return all corpus inputs.
        """

        return list(self.inputs)

    # =========================================================
    # SIZE
    # =========================================================

    def size(self):
        """
        Return number of corpus inputs.
        """

        return len(self.inputs)

    # =========================================================
    # PYTHON LEN()
    # =========================================================

    def __len__(self):
        return len(self.inputs)

    # =========================================================
    # ITERATION
    # =========================================================

    def __iter__(self):
        return iter(self.inputs)

    # =========================================================
    # REPRESENTATION
    # =========================================================

    def __repr__(self):

        return (
            f"Corpus("
            f"size={len(self.inputs)}, "
            f"directory='{self.directory}'"
            f")"
        )

    # =========================================================
    # SAVE CORPUS
    # =========================================================

    def _save(self):
        """
        Persist corpus inputs and coverage metadata.
        """

        metadata = []

        for index, data in enumerate(
            self.inputs
        ):

            filename = (
                f"input_{index:04d}.bin"
            )

            input_path = (
                self.directory /
                filename
            )

            # Save binary input
            with open(
                input_path,
                "wb"
            ) as file:

                file.write(data)

            metadata.append(
                {
                    "file": filename,
                    "coverage": sorted(
                        self.coverage[index]
                    )
                }
            )

        # Save metadata
        temporary_file = (
            self.directory /
            "metadata.tmp"
        )

        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                metadata,
                file,
                indent=4
            )

        # Replace old metadata atomically
        temporary_file.replace(
            self.metadata_file
        )

    # =========================================================
    # LOAD CORPUS
    # =========================================================

    def _load(self):
        """
        Load previously persisted corpus.

        Invalid or missing entries are skipped safely.
        """

        if not self.metadata_file.exists():
            return

        try:

            with open(
                self.metadata_file,
                "r",
                encoding="utf-8"
            ) as file:

                metadata = json.load(file)

        except (
            OSError,
            json.JSONDecodeError
        ):

            return

        if not isinstance(
            metadata,
            list
        ):

            return

        for entry in metadata:

            if not isinstance(
                entry,
                dict
            ):

                continue

            filename = entry.get(
                "file"
            )

            coverage = entry.get(
                "coverage",
                []
            )

            if not filename:
                continue

            input_path = (
                self.directory /
                filename
            )

            try:

                with open(
                    input_path,
                    "rb"
                ) as file:

                    data = file.read()

            except OSError:

                continue

            if data in self.inputs:
                continue

            try:

                coverage = {
                    int(line)
                    for line in coverage
                }

            except (
                TypeError,
                ValueError
            ):

                coverage = set()

            self.inputs.append(
                data
            )

            self.coverage.append(
                coverage
            )