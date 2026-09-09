# CGFuzz

### Coverage-Guided Mutation Fuzzer

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#requirements)
[![Tests](https://img.shields.io/badge/tests-112%20passing-brightgreen)](#testing)
[![Release](https://img.shields.io/badge/release-v1.0.0-blue)](#release)
[![Status](https://img.shields.io/badge/status-research%20prototype-orange)](#current-scope)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)

CGFuzz is a modular **coverage-guided mutation fuzzing framework** that combines feedback-driven input generation with automated crash triage. It supports Python targets, native C/C++ execution, line/edge/bitmap coverage, ASan/UBSan integration, persistent worker execution, distributed workers, corpus minimization, and persistent crash analysis.

Instead of treating every generated input equally, CGFuzz uses **execution feedback** to identify inputs that discover previously unseen coverage and promotes those inputs into a coverage-guided scheduling population — so the fuzzer spends its time where it actually learns something new about the target.

---

## Table of Contents

- [Why CGFuzz](#why-cgfuzz)
- [How It Works](#how-it-works)
- [Features](#features)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Requirements](#requirements)
- [Testing](#testing)
- [Evaluation](#evaluation)
- [Architecture](#architecture)
- [Crash Analysis Pipeline](#crash-analysis-pipeline)
- [Native and Sanitizer Support](#native-and-sanitizer-support)
- [Persistent and Distributed Execution](#persistent-and-distributed-execution)
- [Project Structure](#project-structure)
- [Engineering Design](#engineering-design)
- [Current Scope](#current-scope)
- [Roadmap](#roadmap)
- [Project Philosophy](#project-philosophy)
- [Release](#release)
- [Contributing](#contributing)
- [License](#license)

---

## Why CGFuzz

Most introductory fuzzers stop at "generate random input, see if it crashes."

CGFuzz closes that loop: when a crash is discovered, the input is automatically classified, minimized to a smaller reproducing case, replayed to verify reproducibility, deduplicated against a persistent crash database, and stored as a structured failure artifact.

As of **v1.0.0**, CGFuzz goes beyond a Python-only prototype. The implementation includes native C/C++ target execution, GCC/gcov-based native coverage, ASan/UBSan integration, line and edge coverage, bitmap feedback, persistent worker execution, coordinator-mediated distributed fuzzing, corpus minimization, and automated end-to-end validation. See [Features](#features) for the capability list.

---

## How It Works

```text
Seed Input
    |
    v
  Mutator
    |
    v
 Executor
    |
    +------------------+
    |                  |
    v                  v
Coverage            Crash
    |                  |
    v                  v
 Corpus            Classifier
    |                  |
    v                  v
Scheduler          Minimizer
    |                  |
    ^                  v
    |              Reproducer
    |                  |
    |                  v
    |              Crash DB
    |
    +<------ Feedback Loop ------+
Seed Input — provides the starting fuzzing input.
Mutator — applies byte-level mutation strategies to generate candidates.
Executor — runs Python or native C/C++ targets with timeout handling and optional sanitizer support.
Coverage — new line, edge, or bitmap coverage promotes an input into the corpus.
Scheduler — prioritizes interesting corpus entries for future mutation.
Crash Pipeline — detected crashes are classified, minimized, reproduced, deduplicated, and persisted.
Distributed Workers — multiple workers can execute fuzzing tasks while the coordinator synchronizes corpus and scheduler state.
Features
Category	Capabilities
Fuzzing core	Byte-level mutation, coverage-guided scheduling, dynamic corpus management
Coverage	Line coverage, edge coverage, bitmap feedback
Crash handling	Detection, classification, minimization, reproduction, deduplication, persistent artifacts
Native execution	C/C++ target execution, GCC/gcov coverage
Sanitizers	ASan and UBSan integration
Performance	Persistent worker execution
Distributed	Multi-worker execution with coordinator-mediated corpus/scheduler synchronization
Interface	CLI campaign configuration and statistics
Testing	112 passing tests

This table is the canonical feature list for this README. Current Scope and Roadmap reference it rather than repeating the full list.

Quickstart
Clone the repository
git clone https://github.com/aditipradhan18/CGfuzz.git
cd CGfuzz
Install the testing dependency
pip install pytest
Run a fuzzing campaign
python -m src.cli --target src/target.py
Run a configured campaign
python -m src.cli \
    --target src/target.py \
    --seed CRASH \
    --iterations 100 \
    --timeout 1 \
    --max-input-size 4096 \
    --reproduction-attempts 3 \
    --workers 1
View CLI options
python -m src.cli --help
Usage

The command-line interface supports:

--target                  Target Python or native executable
--seed                    Initial fuzzing seed
--iterations              Number of mutation/execution iterations
--timeout                 Per-execution timeout
--max-input-size          Maximum accepted input size
--reproduction-attempts   Retries when confirming crash reproducibility
--workers                 Number of fuzzing workers

Example with multiple workers:

python -m src.cli \
    --target src/target.py \
    --seed CRASH \
    --iterations 1000 \
    --timeout 1 \
    --max-input-size 4096 \
    --reproduction-attempts 3 \
    --workers 2
Requirements
Python 3.10+
pytest for development/testing
GCC/gcov support for native C/C++ coverage workflows
A compiler/runtime environment capable of providing ASan or UBSan for sanitizer-backed native runs
Testing

Run the complete regression suite:

python -m pytest -q

Current validation:

112 passed

The suite covers mutation behavior, corpus management, line/edge/bitmap coverage, coverage-guided scheduling, Python and native target execution, timeout handling, input sanitization, crash classification and persistence, crash minimization and reproduction, distributed worker execution, fuzzer orchestration, CLI execution, and end-to-end campaign behavior.

Evaluation

CGFuzz includes a benchmark suite for evaluating fuzzing effectiveness, execution performance, coverage, corpus efficiency, scheduler behavior, sanitization, crash handling, and end-to-end operation.

Baseline vs CGFuzz

A measured 100-iteration comparison against the included target produced:

Metric	Baseline	CGFuzz
Executions	101	101
Execution rate	9.34 exec/s	3.36 exec/s
Crashes found	2	11
Coverage lines	28	27
Timeouts	0	0
Corpus size	101	154
Reproduced crashes	—	11
Bitmap coverage	—	25
Scheduler entries	—	4

Observed differences in this run:

Throughput change       : -64.03%
Crash discovery         : 5.50x
Crash increase          : +450.00%
Coverage change         : -1 line (-3.57%)
Corpus increase         : +53 (+52.48%)

Benchmark caveat: The 5.50x crash-discovery result is specific to this measured run. Fuzzing results are stochastic and vary with the target, seed, mutation sequence, and execution environment.

Coverage note: CGFuzz reached one fewer line than the baseline in this run while finding substantially more crashes. The one-line difference does not by itself indicate a regression: coverage totals and crash discovery measure different outcomes, and the exact paths explored vary with the mutation sequence.

Throughput note: The lower CGFuzz campaign throughput reflects additional work for feedback collection, corpus management, scheduling, crash analysis, minimization, reproduction, and persistence.

Execution Performance

A separate real-subprocess benchmark measured:

Executions            : 100
Normal executions     : 91
Crashes               : 9
Timeouts              : 0
Execution rate        : 9.12 exec/sec
Avg execution time    : 107.52 ms
Median execution time : 100.65 ms
Min execution time    : 88.70 ms
Max execution time    : 194.64 ms

These measurements represent target execution performance and should be distinguished from full campaign duration, which includes CGFuzz processing overhead.

Persistent Execution

A verified persistent-worker comparison measured approximately:

Persistent worker : 281.92 exec/sec
Normal subprocess :   6.28 exec/sec
Approx. speedup   : 45x

Results vary with the target and execution environment.

End-to-End Demonstration

The final end-to-end benchmark exercises the complete pipeline:

Sanitizer -> Executor -> Coverage -> Scheduler -> Mutation
    -> Crash Analysis -> Minimization -> Reproduction -> Crash Database

A verified final demonstration produced:

Iterations          : 30
Executions           : 31
Crashes found        : 3
Reproduced crashes   : 3
Timeouts             : 0
Rejected inputs      : 0
Coverage lines       : 25
Bitmap coverage      : 23
Corpus size          : 3
Scheduler entries    : 3
Crash binary files   : 2
Crash report files   : 3
Corpus files         : 3

CGFuzz end-to-end final demo: PASS
<details> <summary><strong>Architecture</strong> — expand for the system diagram</summary>

CGFuzz follows a modular architecture where each major responsibility is isolated behind a dedicated component.

                         +----------------+
                         |      CLI       |
                         +-------+--------+
                                 |
                                 v
                         +----------------+
                         |     CGFuzz     |
                         | Campaign Engine|
                         +-------+--------+
                                 |
               +-----------------+------------------+
               |                 |                  |
               v                 v                  v
        +-------------+   +-------------+   +-------------+
        |   Mutator   |   |  Scheduler  |   |   Corpus    |
        +------+------+   +------+------+   +------+------+
               |                 |                  |
               +-----------------+------------------+
                                 |
                                 v
                         +----------------+
                         |    Executor    |
                         +-------+--------+
                                 |
                                 v
                         +----------------+
                         | Target Program |
                         +-------+--------+
                                 |
                    +------------+------------+
                    |                         |
                    v                         v
             +-------------+           +-------------+
             |   Coverage  |           |    Crash    |
             |   Tracking  |           |   Pipeline  |
             +-------------+           +------+------+
                                             |
                         +-------------------+------------------+
                         |                   |                  |
                         v                   v                  v
                  +-------------+    +-------------+    +-------------+
                  | Classifier  |    |  Minimizer  |    | Reproducer |
                  +-------------+    +-------------+    +------+------+
                                                                    |
                                                                    v
                                                              +-----------+
                                                              |  Crash DB |
                                                              +-----------+
Core Components
Component	Responsibility
Fuzzer	Orchestrates the complete fuzzing campaign
CLI	Converts command-line configuration into a fuzzing campaign
Executor	Executes Python/native targets and collects execution feedback
Mutator	Generates mutated test cases
Corpus	Stores interesting inputs
CoverageTracker	Maintains observed coverage
CoverageGuidedScheduler	Prioritizes promising corpus inputs
CoverageBitmap	Represents bitmap coverage feedback
CrashClassifier	Categorizes target failures
CrashMinimizer	Reduces crashing inputs
CrashReproducer	Verifies reproducibility
CrashDatabase	Persists and deduplicates crash artifacts
DistributedWorkerPool	Executes fuzzing tasks across workers
</details>
<details> <summary><strong>Crash Analysis Pipeline</strong> — expand for crash-processing details</summary>

Crash detection. CGFuzz distinguishes normal execution, crashes, and timeouts.

Crash classification. Crashes are assigned normalized categories such as RuntimeError, ValueError, TypeError, IndexError, KeyError, AttributeError, ZeroDivisionError, MemoryError, AssertionError, SystemExit, and unknown failures. Native sanitizer failures can also be processed through their diagnostic output.

Crash minimization. The minimizer attempts to remove unnecessary bytes while preserving the failure:

Original Input
      |
      v
Remove Candidate Byte
      |
      v
Execute Again
      |
   +--+--+
   |     |
 Crash  No Crash
   |     |
   v     v
 Keep  Restore
   |
   v
Continue

Crash reproduction. Minimized inputs are replayed multiple times to verify reproducibility:

Attempts : 3
Crashes  : 3
Normal   : 0
Timeouts : 0

Crash deduplication. Normalized crash information is used to generate a persistent crash signature so repeated instances of the same failure can be recognized.

Persistent crash artifacts. Crash artifacts are stored for later inspection:

crashes/
├── crash_<hash>.bin
└── crash_<hash>.txt

The binary file stores the minimized crashing input. The metadata file records the crash type, crash message, original/minimized input size, reproduction attempts and results, and reproducibility status.

The crash database is persistent across campaigns. A database-level unique-crash count can therefore include artifacts from previous runs and should not be interpreted as the number of unique crashes discovered by one campaign.

</details>
<details> <summary><strong>Native and Sanitizer Support</strong> — expand for native execution details</summary>

CGFuzz supports native C/C++ target execution in addition to Python targets.

Native support includes:

Native executable execution
GCC/gcov line coverage
AddressSanitizer integration
UndefinedBehaviorSanitizer integration
Sanitizer-aware crash classification
Timeout handling

Native test targets are included in the repository to validate these execution paths.

</details>
<details> <summary><strong>Persistent and Distributed Execution</strong> — expand for worker architecture</summary>

Persistent execution. CGFuzz includes a persistent worker execution mode that reuses worker processes across executions instead of creating a new worker process for every input. This reduces process-launch overhead for suitable workloads.

Distributed fuzzing. CGFuzz supports multiple workers through a coordinator-mediated worker pool. The coordinator maintains shared corpus state, coverage state, bitmap feedback, scheduler state, and campaign statistics. Workers execute fuzzing tasks in parallel and return results to the coordinator, which incorporates newly discovered feedback into the campaign state.

</details>
<details> <summary><strong>Project Structure</strong> — expand for repository layout</summary>
CGFuzz/
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── corpus.py
│   ├── corpus_minimizer.py
│   ├── coverage_guided.py
│   ├── coverage_tracker.py
│   ├── bitmap.py
│   ├── crash_classifier.py
│   ├── crash_database.py
│   ├── crash_minimizer.py
│   ├── crash_reproducer.py
│   ├── distributed.py
│   ├── executor.py
│   ├── fuzzer.py
│   ├── mutator.py
│   ├── sanitizer.py
│   └── target.py
│
├── tests/
│   ├── corpus_test.py
│   ├── corpus_minimizer_test.py
│   ├── crash_classifier_test.py
│   ├── crash_database_test.py
│   ├── crash_reproducer_test.py
│   ├── executor_test.py
│   ├── fuzzer_test.py
│   ├── integration_test.py
│   ├── mutator_test.py
│   ├── process_test.py
│   ├── sanitizer_test.py
│   ├── test_bitmap.py
│   ├── test_fuzzer_end_to_end.py
│   └── distributed_test.py
│
├── benchmarks/
│   ├── baseline.py
│   ├── cgfuzz_benchmark.py
│   ├── corpus_efficiency_benchmark.py
│   ├── coverage_benchmark.py
│   ├── crash_directory_benchmark.py
│   ├── crash_minimization_benchmark.py
│   ├── crash_reproduction_benchmark.py
│   ├── end_to_end_benchmark.py
│   ├── execution_performance_benchmark.py
│   ├── sanitizer_benchmark.py
│   └── scheduler_benchmark.py
│
├── native_targets/
│   ├── vulnerable.c
│   ├── ubsan_test.c
│   └── persistent_timeout_test.py
│
├── sanitizer_test.c
├── README.md
└── .gitignore
</details>
<details> <summary><strong>Engineering Design</strong> — expand for design principles</summary>

Separation of concerns. Each major subsystem has a dedicated responsibility. The campaign engine coordinates execution while mutation, coverage, scheduling, crash analysis, and persistence remain independently testable.

Feedback-driven exploration. The scheduler is driven by execution feedback rather than treating every corpus entry equally:

Program Behavior -> Coverage -> Input Selection -> Mutation -> Program Behavior

Reproducibility. Crashing inputs are minimized and replayed multiple times before reproduction metadata is recorded.

Persistent failure artifacts. Crashes are converted into persistent artifacts rather than being lost when a fuzzing campaign terminates. This separates discovery from analysis and allows failures to be investigated after the campaign has completed.

Extensible execution layer. The executor provides an abstraction between the fuzzing engine and the target implementation, allowing additional target backends to be introduced without rewriting the campaign engine.

</details>
Current Scope

CGFuzz v1.0.0 is a research prototype with a complete feedback loop across Python and native C/C++ targets, implementing the capabilities listed in Features plus benchmark and end-to-end validation.

CGFuzz is best suited for research, coursework, experimentation, and as a reference implementation for learning how coverage-guided fuzzers work end to end.

It should not currently be described as a production replacement for mature native fuzzers such as AFL++, libFuzzer, or Honggfuzz.

Roadmap

Completed — v1.0.0

All capabilities listed in the Features section are implemented and validated, together with the automated regression suite, benchmark suite, and end-to-end validation.

Future work

 More advanced native instrumentation
 Structure-aware / grammar-based mutation
 More scalable distributed synchronization
 Additional target backends
 Advanced performance-aware scheduling
 Hardware-assisted instrumentation
Project Philosophy

CGFuzz is built around a simple principle:

A fuzzer should learn from every execution.

An execution that discovers nothing should not be treated the same as an execution that unlocks previously unexplored behavior.

A crash should not simply become a log line — it should become:

Reproducible -> Minimized -> Classified -> Deduplicated -> Persistent Failure Artifact

The goal is not merely to generate more inputs.

The goal is to spend execution budget intelligently and turn program behavior into actionable testing information.

Release

Current release: CGFuzz v1.0.0

Release commit: ed33411

Contributing

Issues and pull requests are welcome.

When adding a new mutation strategy, coverage backend, execution mode, or crash-analysis feature, please include corresponding tests.

License

MIT — see LICENSE for details.