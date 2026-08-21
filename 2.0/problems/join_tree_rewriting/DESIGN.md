## Task

Restore cardinality-aware binary join-tree rewriting before two-phase semijoin lowering, preserving exact query results while minimizing end-to-end latency. The public substrate retains the upstream binary-plan representation, IR parser, semijoin lowering, and a challenge-neutral `rewrite_policy.py::rewrite_plan` hook; the hidden judge retains fixed non-lowerable Stats-CEB IR plans, the obtainable lowercase parquet data, the upstream conversion scripts and timing CSV, and the reproduced join executable.

## Why this is a real task

The editable hook must return a legal equivalent tree for every real optimizer plan before any timing is counted. Different legal trees produce different multisemijoin schedules and flattening behavior in the actual engine. On the expanded workload the upstream dynamic-programming policy scores 65 on development and 62 on final, while the identity baseline scores zero. The prior real-agent trace required 28 genuine policy iterations to move several development points and only narrowly beat the disjoint final reference, establishing a near-reference frontier rather than a trivial validity exercise.

## Data / workload design

Development and final evaluation use disjoint fixed twelve-query halves selected from the artifact's non-lowerable Stats-CEB IR corpus. Each half has two four-relation, two five-relation, seven six-relation, and one seven-relation plan. The judge runs the artifact's `parquet-zstd-lowercase` archive, not generated relations. A one-repetition correctness pass executes the original binary, reference, and candidate plans and aborts on any output difference. A separate timing pass places candidate and reference plans in both order positions for seven repetitions, yielding fourteen observations per method and query without repeatedly paying for the slower binary plan.

## Scoring

For each query, `recorded_gain_q` is the median recorded BinaryJoin time divided by median recorded two-phase time. The live run computes `relative_q = median(reference time) / median(candidate time)`, and `gain = geometric_mean(recorded_gain_q * relative_q)`. The continuous transform is `100 * gain / (1 + gain)`, but both bounded and unbounded reported scores are rounded to the nearest integer so sub-point timing movement cannot decide a trial. Byte-identical plans receive an exact relative of one. Symmetric order and fourteen-sample medians reduce cache and warm-up bias. Timing is unreachable until patch policy, structural equivalence, upstream lowering, process completion, and exact engine output checks all pass.

## Known risks

The fixed workload can still reward broad Stats-CEB-specific choices, although twelve cases, a 25-submission budget, and disjoint hidden final plans sharply reduce per-query fitting. Different executable plans retain host timing noise, now deliberately hidden below one score point. Absolute calibration comes from recorded artifact timings while relative improvement is measured live, so a future engine or hardware change should trigger recalibration. The bundled x86-64 glibc executable must be rebuilt if the runtime family changes. Public upstream representation and invariant names may still help source identification, but the direct bibliographic and contribution-path lookup route has been removed.

## Changes made in refinement

- Replaced the random-tree simulator and challenge-only cardinality formula with fixed upstream Stats-CEB plans, real parquet data, and actual end-to-end execution.
- Added the reproduced 80 MiB author runner, both upstream Rust source crates, parser/conversion scripts, and the exact artifact timing CSV used for calibration.
- Added paired paper/candidate lowering and symmetric repeated timing, with the upstream binary plan included in every output-equality comparison.
- Made identical reference plans noise-free while retaining live paired timing for genuinely different plans.
- Fixed `make_submission.sh` so `/app/solution.patch` and the injected `/app/submit.sh` do not fail the egress allowlist.
- Added a test that applies the reference in a solver checkout, pre-creates both egress files, generates the patch through the public helper, and scores it successfully.
- Removed the unused synthetic workload runner and obsolete weak fixture.
- Reduced solution-direction prose in the public design-space section and updated all workload, scoring, timeout, and resource claims.

## Round 1 fixes

- Replaced the searchable contribution filename and entry point with challenge-neutral `rewrite_policy.py::rewrite_plan`; adapted the hidden upstream reference only at that interface boundary.
- Removed the exact paper title, author list, original policy path, and original runner name from the solver statement.
- Expanded each disjoint suite from four to twelve real artifact queries with matched 4/5/6/7-relation coverage.
- Increased symmetric timing repetitions from five to seven, producing fourteen observations per method and query.
- Split correctness from timing so the original binary plan runs once per query while reference/candidate timing remains symmetric and fits the timeout.
- Reduced the development-submission budget from 100 to 25 to constrain feedback-driven workload fitting.
- Rounded reported bounded and unbounded scores to integer points; two post-fix independent full runs of the same alternative policy both report 65 despite underlying aggregate speedups of 1.828 and 1.845.
- Re-ran full development and final reference preflight: the expanded reference scores 65 and 62 respectively.

## Round 2 fixes

- Preserved the real 12+12 Stats-CEB workload, correctness gates, neutral hook, 25-submission budget, integer reward, and full upstream reference because the auditor found no required revision or reward-hacking path.
- Split the former combined engine failure diagnostic into output-equality rejection versus other executable-plan rejection.
- Kept both diagnostics query-neutral: they disclose neither hidden query identity nor plan contents.
- Re-ran evaluator properties and the full reference after the diagnostic-only change.
