import sys
from pathlib import Path

# =============================================================
# PROJECT ROOT
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================
# IMPORT CGFUZZ
# =============================================================

from src.executor import Executor
from src.fuzzer import Fuzzer


# =============================================================
# BENCHMARK
# =============================================================

def run_cgfuzz():

    target = PROJECT_ROOT / "src" / "target.py"

    executor = Executor(
        target,
        timeout=1.0
    )

    fuzzer = Fuzzer(
        executor=executor,
        iterations=100,
        max_input_size=4096,
        reproduction_attempts=3
    )

    # Use a NON-CRASHING seed.
    # This prevents the crash-minimization/reproduction
    # pipeline from dominating this scheduling benchmark.
    seed = b"SEED"

    fuzzer.run(seed)


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":
    run_cgfuzz()