# CGFuzz

### Coverage-Guided Mutation Fuzzer

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#)
[![Tests](https://img.shields.io/badge/tests-86%20passing-brightgreen)](#testing)
[![Status](https://img.shields.io/badge/status-research%20prototype-orange)](#current-scope)
CGFuzz is a modular **coverage-guided mutation fuzzing framework** designed to automatically explore program behavior, discover crashes, and turn raw failures into reproducible, minimized, and deduplicated test cases.

Instead of treating every generated input equally, CGFuzz uses **execution feedback** to identify inputs that discover previously unseen coverage and promotes those inputs into a coverage-guided scheduling population.

The result is a continuous feedback loop:

```text
              ┌───────────────────┐
              │    Seed Input     │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │      Mutator      │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │     Executor      │
              └─────────┬─────────┘
                        │
                ┌───────┴───────┐
                │               │
                ▼               ▼
           Coverage           Crash
                │               │
                ▼               ▼
             Corpus         Classifier
                │               │
                ▼               ▼
           Scheduler        Minimizer
                │               │
                │               ▼
                │          Reproducer
                │               │
                │               ▼
                │         Crash Database
                │
                └───────► Mutation
Why CGFuzz?

Pure random mutation can repeatedly generate inputs that exercise code the fuzzer has already explored.

CGFuzz closes that loop by using coverage as feedback.

When an input discovers previously unseen coverage:

candidate coverage
        -
global coverage
        =
new coverage

If new coverage exists, the input becomes interesting and can be retained for future mutation.

This creates a continuous exploration cycle:

Execute
   ↓
Measure Coverage
   ↓
Discover New Behavior
   ↓
Retain Interesting Input
   ↓
Prioritize Input
   ↓
Mutate
   ↓
Execute Again

CGFuzz also processes crashes through an automated analysis pipeline:

Detect
  ↓
Classify
  ↓
Minimize
  ↓
Reproduce
  ↓
Deduplicate
  ↓
Persist
Technical Highlights
Coverage-Guided Scheduling

CGFuzz maintains a scheduling population containing inputs associated with coverage discoveries.

Inputs are scored using their coverage characteristics and input size, allowing the scheduler to preferentially select promising inputs for further mutation.

This moves the engine beyond uniform random corpus selection.

Mutation Engine

The mutation layer generates new candidates from existing inputs using byte-level mutation strategies including:

Bit flipping
Byte flipping
Byte insertion
Byte deletion
Byte replacement
Arithmetic mutation
Repeated mutation

The mutator operates independently from execution and scheduling, allowing the mutation strategy to evolve without redesigning the campaign engine.

Execution Isolation

The executor provides a consistent interface between CGFuzz and the target program.

Each execution produces normalized information including:

Execution Status
Exit Code
stdout
stderr
Execution Duration
Coverage

Target failures and timeouts are converted into explicit execution states so the campaign engine can process them consistently.

Coverage Tracking

CGFuzz collects target execution coverage and maintains a global set of observed coverage locations.

Only inputs that contribute previously unseen coverage are promoted as interesting corpus entries.

This prevents the corpus from becoming dominated by inputs that repeatedly exercise the same behavior.

Automated Crash Triage

A crash is not simply written to a log.

CGFuzz processes failures through:

Crash
  │
  ▼
Classification
  │
  ▼
Minimization
  │
  ▼
Reproduction
  │
  ▼
Signature Generation
  │
  ▼
Deduplication
  │
  ▼
Persistent Storage

This turns a raw execution failure into a structured debugging artifact.

Crash Analysis Pipeline
1. Crash Detection

The executor identifies abnormal target execution and reports it to the campaign engine.

CGFuzz distinguishes:

Normal execution
Crashes
Timeouts
2. Crash Classification

The crash classifier extracts a normalized crash category and associated message.

Supported categories include:

RuntimeError
ValueError
TypeError
IndexError
KeyError
AttributeError
ZeroDivisionError
MemoryError
AssertionError
SystemExit
Unknown
3. Crash Minimization

A crashing input can contain data that is irrelevant to the failure.

CGFuzz attempts to remove unnecessary bytes while preserving the crash.

Original Input
      │
      ▼
Remove Candidate Byte
      │
      ▼
Execute Again
      │
 ┌────┴────┐
 │         │
Crash     No Crash
 │         │
 ▼         ▼
Keep     Restore
 │
 └──────► Continue

The result is a smaller reproducer that is easier to analyze.

4. Crash Reproduction

The minimized input is executed repeatedly to verify that the failure is reproducible.

Example:

Attempts : 3
Crashes  : 3
Normal   : 0
Timeouts : 0

This helps distinguish stable failures from potentially inconsistent ones.

5. Crash Deduplication

A normalized crash signature is generated from the classified crash information.

The signature is hashed using SHA-256 to produce a compact crash identifier.

Repeated occurrences of the same signature can therefore be recognized as duplicates.

6. Persistent Crash Database

Unique crash artifacts are persisted for later inspection.

Example:

crashes/
├── crash_<hash>.bin
└── crash_<hash>.txt

The binary artifact stores the minimized crashing input.

The metadata artifact records information such as:

Crash type
Crash message
Original input size
Minimized input size
Reproduction attempts
Reproduction results
Reproducibility status
Architecture

CGFuzz follows a modular architecture where each major responsibility is isolated behind a dedicated component.

                         ┌───────────────┐
                         │      CLI      │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │     CGFuzz    │
                         │ Campaign      │
                         │ Engine        │
                         └───────┬───────┘
                                 │
               ┌─────────────────┼─────────────────┐
               │                 │                 │
               ▼                 ▼                 ▼
         ┌──────────┐      ┌──────────┐      ┌────────────┐
         │ Mutator  │      │  Corpus  │      │ Scheduler  │
         └────┬─────┘      └────┬─────┘      └──────┬─────┘
              │                 │                   │
              └─────────────────┼───────────────────┘
                                │
                                ▼
                         ┌───────────────┐
                         │    Executor   │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │ Target Program│
                         └───────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
             ┌──────────────┐          ┌──────────────┐
             │   Coverage   │          │    Crash     │
             │   Tracking   │          │   Pipeline   │
             └──────┬───────┘          └──────┬───────┘
                    │                         │
                    ▼                         ▼
                 Corpus                 Classifier
                    │                         │
                    ▼                         ▼
                Scheduler                Minimizer
                                              │
                                              ▼
                                         Reproducer
                                              │
                                              ▼
                                         Crash DB
Core Components
Component	Responsibility
Fuzzer	Orchestrates the complete fuzzing campaign
CLI	Converts command-line configuration into a fuzzing campaign
Executor	Executes the target and collects execution results
Mutator	Generates mutated test cases
Corpus	Stores inputs that discover new coverage
Coverage Tracker	Maintains observed execution coverage
Scheduler	Prioritizes promising corpus inputs
Sanitizer	Enforces input-level safety constraints
Crash Classifier	Categorizes target failures
Crash Minimizer	Reduces crashing inputs
Crash Reproducer	Verifies crash reproducibility
Crash Database	Persists and deduplicates crash artifacts
Project Structure
CGFuzz/
│
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── corpus.py
│   ├── coverage_guided.py
│   ├── coverage_tracker.py
│   ├── crash_classifier.py
│   ├── crash_database.py
│   ├── crash_minimizer.py
│   ├── crash_reproducer.py
│   ├── executor.py
│   ├── fuzzer.py
│   ├── mutator.py
│   ├── sanitizer.py
│   └── target.py
│
├── tests/
│   ├── corpus_test.py
│   ├── crash_classifier_test.py
│   ├── crash_database_test.py
│   ├── crash_reproducer_test.py
│   ├── executor_test.py
│   ├── fuzzer_test.py
│   ├── integration_test.py
│   ├── mutator_test.py
│   ├── process_test.py
│   ├── sanitizer_test.py
│   └── test_fuzzer_end_to_end.py
│
├── docs/
├── corpus/
├── crashes/
│
├── README.md
└── .gitignore
Installation
Requirements
Python 3.10+
pytest for development/testing

Clone the repository:

git clone <repository-url>
cd CGFuzz

Create a virtual environment:

python -m venv .venv

Windows:

.venv\Scripts\activate

Install testing dependencies:

pip install pytest
Quickstart

Run CGFuzz against the included target:

python -m src.cli --target src/target.py

Specify a seed:

python -m src.cli `
    --target src/target.py `
    --seed CRASH

Run a larger campaign:

python -m src.cli `
    --target src/target.py `
    --seed CRASH `
    --iterations 1000

Configure the execution timeout:

python -m src.cli `
    --target src/target.py `
    --seed CRASH `
    --iterations 1000 `
    --timeout 1

Configure crash reproduction:

python -m src.cli `
    --target src/target.py `
    --seed CRASH `
    --iterations 1000 `
    --reproduction-attempts 3

View all CLI options:

python -m src.cli --help
Configuration
Option	Description	Default
--target	Target Python program	Required
--seed	Initial fuzzing input	CRASH
--iterations	Number of mutation iterations	1000
--timeout	Target execution timeout	1.0s
--max-input-size	Maximum accepted input size	4096 bytes
--reproduction-attempts	Crash reproduction attempts	3

Example:

python -m src.cli `
    --target src/target.py `
    --seed FUZZ `
    --iterations 5000 `
    --timeout 1 `
    --max-input-size 4096 `
    --reproduction-attempts 3
Campaign Metrics

CGFuzz records campaign-level performance and discovery metrics.

Execution Metrics
Total executions
Execution rate
Average execution time
Campaign duration
Discovery Metrics
Total coverage
Coverage discoveries
Corpus size
Scheduler population
Failure Metrics
Crashes found
Crash rate
Unique crashes
Reproduced crashes
Timeouts
Rejected inputs

These metrics make it possible to evaluate both fuzzing effectiveness and execution efficiency.

# Benchmark Snapshot

A representative 1,000-iteration campaign produced:

```text
============================================================
FUZZING CAMPAIGN STATISTICS
============================================================
Campaign duration : 133.80 seconds
Executions        : 1001
Execution rate    : 7.48 exec/sec
Avg exec time     : 76.68 ms

Crashes found     : 49
Reproduced        : 49

Timeouts          : 0
Rejected inputs   : 0

Coverage lines    : 30
Coverage finds    : 6
Corpus size       : 101
Scheduler entries : 6
============================================================
What this demonstrates

The campaign successfully:

executed 1,000+ target inputs
discovered new coverage
expanded the fuzzing corpus
used coverage-guided scheduling
detected 49 crashes
reproduced all 49 discovered crashes
minimized crash inputs
persisted crash artifacts
completed without target timeouts or rejected inputs

Note: The crash database is persistent across campaigns. Its total unique-crash count can therefore include artifacts from previous runs and should not be interpreted as the number of unique crashes discovered by a single campaign.

Testing

CGFuzz uses unit, integration, and end-to-end tests.

Run the complete suite:

python -m pytest -q

Current validation:

86 tests passing
Test Coverage Areas

The test suite validates:

Mutation behavior
Corpus management
Coverage tracking
Coverage-guided scheduling
Target execution
Timeout handling
Input sanitization
Crash classification
Crash persistence
Crash minimization
Crash reproduction
Fuzzer orchestration
CLI execution
End-to-end campaign behavior
End-to-End Validation

CGFuzz includes an integration test that exercises the complete pipeline:

Seed
 ↓
Sanitizer
 ↓
Executor
 ↓
Coverage Collection
 ↓
Coverage-Guided Scheduler
 ↓
Mutation
 ↓
Crash Detection
 ↓
Crash Classification
 ↓
Crash Minimization
 ↓
Crash Reproduction
 ↓
Crash Deduplication
 ↓
Crash Database
 ↓
Campaign Statistics

The CLI is also executed as a separate process during testing to verify that the public command-line interface can successfully launch a complete fuzzing campaign.

Engineering Design
Separation of Concerns

Each major subsystem has a dedicated responsibility.

The fuzzer orchestrates the campaign while execution, mutation, scheduling, coverage, crash analysis, and persistence remain independently testable components.

Feedback-Driven Exploration

The scheduler is driven by actual execution coverage rather than treating every corpus entry equally.

This creates a feedback relationship between:

Program Behavior
       ↓
Coverage
       ↓
Input Selection
       ↓
Mutation
       ↓
Program Behavior
Reproducibility

Crashing inputs are minimized and replayed multiple times before reproduction metadata is recorded.

This makes the resulting crash artifacts significantly more useful for debugging.

Persistent Failure Artifacts

Crashes are converted into persistent artifacts rather than being lost when a fuzzing campaign terminates.

This separates:

Discovery

from:

Analysis

and allows failures to be investigated after the fuzzing campaign has completed.

Extensible Execution Layer

The executor provides an abstraction between the fuzzing engine and target implementation.

This is intentionally designed to make future target backends possible without rewriting the campaign engine.

Current Scope

CGFuzz is currently a Python-based fuzzing research prototype.

The included target is intentionally structured with deterministic branches and crash conditions so that the fuzzing engine can be developed and validated reproducibly.

The current implementation demonstrates the architecture and feedback mechanisms of a coverage-guided fuzzer.

It should not currently be described as a production replacement for mature native fuzzers such as AFL++, libFuzzer, or Honggfuzz.

Roadmap
Completed
 Modular fuzzing engine
 Byte-level mutation engine
 Corpus management
 Coverage collection
 Coverage-guided scheduling
 Target execution
 Timeout handling
 Input sanitization
 Crash detection
 Crash classification
 Crash minimization
 Crash reproduction
 Crash deduplication
 Persistent crash database
 Campaign statistics
 Command-line interface
 End-to-end testing
Planned
 Native C/C++ target support
 AddressSanitizer-assisted memory-error detection
 UndefinedBehaviorSanitizer integration
 Native edge/bitmap coverage
 Persistent execution mode
 Fork-server execution
 Corpus minimization
 Performance-aware scheduling
 Performance anomaly detection
 Distributed fuzzing
 Benchmarking against baseline mutation strategies
 Structure-aware / grammar-based mutation
Security Research Direction

The long-term direction of CGFuzz is to extend the current feedback-driven engine toward real native software testing.

The intended evolution is:

Python Fuzzing Prototype
          │
          ▼
Coverage-Guided Engine
          │
          ▼
Native Target Execution
          │
          ▼
Native Coverage Instrumentation
          │
          ▼
ASan / UBSan Integration
          │
          ▼
Advanced Crash Triage
          │
          ▼
Performance-Aware Scheduling
          │
          ▼
Scalable Fuzzing Infrastructure

The modular architecture allows these capabilities to be introduced incrementally without replacing the core campaign engine.

Project Philosophy

CGFuzz is built around a simple principle:

A fuzzer should learn from every execution.

An execution that discovers nothing should not be treated the same as an execution that unlocks previously unexplored behavior.

A crash should not simply become a log line.

It should become:

A reproducible
      ↓
Minimized
      ↓
Classified
      ↓
Deduplicated
      ↓
Persistent
failure artifact.

The goal is not merely to generate more inputs.

The goal is to spend execution budget intelligently and turn program behavior into actionable testing information.