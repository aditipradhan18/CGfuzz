import os
import subprocess
import sys
from pathlib import Path

from src.executor import Executor
from src.fuzzer import Fuzzer


# =============================================================
# PROJECT PATHS
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TARGET_PATH = (
    PROJECT_ROOT
    / "src"
    / "target.py"
)


# =============================================================
# END-TO-END FUZZER TEST
# =============================================================

def test_complete_fuzzing_pipeline(tmp_path, monkeypatch):
    """
    Verify the complete AstraFuzz pipeline:

        Seed
          ↓
        Sanitizer
          ↓
        Executor
          ↓
        Coverage
          ↓
        Scheduler
          ↓
        Mutation
          ↓
        Crash Detection
          ↓
        Classification
          ↓
        Minimization
          ↓
        Reproduction
          ↓
        Crash Database
          ↓
        Statistics
    """

    # ---------------------------------------------------------
    # Use an isolated temporary directory for crash storage.
    # ---------------------------------------------------------

    monkeypatch.chdir(tmp_path)

    # ---------------------------------------------------------
    # Create executor using the real target program.
    # ---------------------------------------------------------

    executor = Executor(
        target=str(TARGET_PATH),
        timeout=1.0
    )

    # ---------------------------------------------------------
    # Create a small fuzzing campaign.
    # ---------------------------------------------------------

    fuzzer = Fuzzer(
        executor=executor,
        iterations=5,
        max_input_size=4096,
        reproduction_attempts=2
    )

    # ---------------------------------------------------------
    # Run the campaign.
    # ---------------------------------------------------------

    fuzzer.run(
        b"CRASH"
    )

    # =========================================================
    # EXECUTION ASSERTIONS
    # =========================================================

    assert fuzzer.executions == 6

    assert fuzzer.executions > 0

    # =========================================================
    # CRASH ASSERTIONS
    # =========================================================

    assert fuzzer.crashes >= 1

    assert fuzzer.reproduced_crashes >= 1

    # =========================================================
    # DATABASE ASSERTIONS
    # =========================================================

    assert fuzzer.crash_database.count() >= 1

    assert len(fuzzer.crash_database) >= 1

    # =========================================================
    # COVERAGE ASSERTIONS
    # =========================================================

    assert len(fuzzer.total_coverage) > 0

    assert fuzzer.coverage_discoveries > 0

    # =========================================================
    # SCHEDULER ASSERTIONS
    # =========================================================

    assert fuzzer.scheduler.size() > 0

    assert not fuzzer.scheduler.is_empty()

    # =========================================================
    # CORPUS ASSERTIONS
    # =========================================================

    assert fuzzer.corpus.size() > 0

    # =========================================================
    # ERROR ASSERTIONS
    # =========================================================

    assert fuzzer.timeouts == 0

    assert fuzzer.rejected_inputs == 0

    # =========================================================
    # STATISTICS ASSERTIONS
    # =========================================================

    stats = fuzzer.get_statistics()

    assert stats["executions"] == 6

    assert stats["crashes"] >= 1

    assert stats["reproduced_crashes"] >= 1

    assert stats["coverage_lines"] > 0

    assert stats["coverage_discoveries"] > 0

    assert stats["corpus_size"] > 0

    assert stats["scheduler_entries"] > 0

    assert stats["campaign_duration"] > 0

    assert stats["executions_per_second"] > 0

    assert stats["average_execution_time"] > 0


# =============================================================
# CLI END-TO-END TEST
# =============================================================

def test_cli_smoke_test(tmp_path):
    """
    Verify that AstraFuzz can be launched through the CLI
    and successfully execute a small fuzzing campaign.
    """

    command = [
        sys.executable,
        "-m",
        "src.cli",
        "--target",
        str(TARGET_PATH),
        "--seed",
        "CRASH",
        "--iterations",
        "1",
        "--timeout",
        "1",
        "--max-input-size",
        "4096",
        "--reproduction-attempts",
        "1",
    ]

    # ---------------------------------------------------------
    # Preserve the project root in PYTHONPATH so that
    # `python -m src.cli` works even when the subprocess
    # runs inside the temporary directory.
    # ---------------------------------------------------------

    environment = os.environ.copy()

    existing_pythonpath = environment.get(
        "PYTHONPATH",
        ""
    )

    if existing_pythonpath:

        environment["PYTHONPATH"] = (
            str(PROJECT_ROOT)
            + os.pathsep
            + existing_pythonpath
        )

    else:

        environment["PYTHONPATH"] = (
            str(PROJECT_ROOT)
        )

    # ---------------------------------------------------------
    # Run the CLI.
    # ---------------------------------------------------------

    result = subprocess.run(
        command,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True
    )

    # =========================================================
    # PROCESS ASSERTIONS
    # =========================================================

    assert result.returncode == 0

    # =========================================================
    # CONFIGURATION ASSERTIONS
    # =========================================================

    assert (
        str(TARGET_PATH)
        in result.stdout
    )

    # =========================================================
    # FUZZER START ASSERTION
    # =========================================================

    assert (
        "STARTING COVERAGE-GUIDED FUZZER"
        in result.stdout
    )

    # =========================================================
    # CAMPAIGN COMPLETION ASSERTIONS
    # =========================================================

    assert (
        "FUZZING CAMPAIGN STATISTICS"
        in result.stdout
    )

    assert (
        "Executions"
        in result.stdout
    )

    # =========================================================
    # ERROR ASSERTION
    # =========================================================

    assert "Traceback" not in result.stderr