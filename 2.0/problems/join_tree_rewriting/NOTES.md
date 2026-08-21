# Reviewer notes
- Task type: Type B — reproduce or surpass the work's contribution.
- The task maps to “Making binary plans well-behaved” in paper Section 6; the author source is `2phase_nsa/binary_plan/rewrite_costbased.py`.
- The reference is the full dynamic-programming repair and minimum build-penalty selection; only its public filename/entry point were adapted to neutral names.
- The substrate is a deletion-only slice of the authors' planner plus one identity stub and submission helper.
- Workloads are two fixed twelve-query halves of the artifact's non-lowerable Stats-CEB IR corpus, run on its obtainable lowercase parquet archive.
- The hidden runner is the reproduced release binary with both upstream Rust crates retained; conversion uses byte-identical scripts and parser/lowering modules.
- Score calibration uses medians from upstream `experiments/statsceb/timings_revision.csv`; live paired medians adjust candidate latency.
- Twelve cases per suite, seven symmetric repetitions, integer score reporting, resource limits, timeouts, and patch policy are challenge constants (not from materials).
- Structural preservation, successful upstream lowering, and the runner's exact result comparison are hard gates before timing.
- Expected valid scores span roughly 35–80, with additional headroom for policies faster than the paper implementation.
- Development calibration: naive 0, expanded upstream reference 65; two alternative-policy trials both report 65 after noise rounding.
- Final preflight: expanded upstream reference 62; identical plan detection makes repeated reference scores exact.

## Leak inventory
- Removed `WellBehavedPlans`, `get_well_behaved_plans`, `merge_left_into_right`, `merge_right_into_left`, and `try_attach`, plus the candidate-set combiner and all storage, search, attachment, and cost-selection bodies.
- Excluded the upstream cost-policy unit-test module, whose assertions encode candidate counts and chosen repaired trees.
- Excluded unselected query plans, notebooks, generated output plans, logs, plots, and unrelated experiment results; retained only the timing CSV used by scoring.
- Omitted upstream README/paper copies and unrelated source trees; no detailed repair description remains in the public substrate.
- Excluded `.git`, caches, bytecode, backups, rejects, and editor files; the retained filename/entry hook is challenge-neutral interface scaffolding.
