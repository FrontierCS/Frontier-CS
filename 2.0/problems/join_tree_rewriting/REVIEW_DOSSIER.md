# cand_001 — Final Review Dossier

## Problem statement

Solvers must implement `rewrite_plan` in `2phase_nsa/binary_plan/rewrite_policy.py`. The function receives a binary equijoin tree composed of shipped `BinaryJoinNode` and `LeafNode` objects and must return an equivalent reassociated tree that can be lowered into the artifact’s two-phase nested-semijoin representation. Only that file may change; the implementation may add private helpers but may import only from `typing` and the shipped `binary_plan` package.

The returned tree must preserve every relation alias, leaf attribute set, estimated cardinality, and equijoin predicate exactly once. Every interior join must use the intersection of the attributes below its children, and its join attributes must occur in the left-most leaf of both child subtrees. The unchanged pipeline validates this invariant, lowers the tree, and checks that its execution result exactly matches both the original binary plan and the calibrated comparison plan.

After correctness and structural validity are established, the objective is to choose a legal tree that minimizes actual execution latency on hidden Stats-CEB plans. Source-policy restrictions prohibit filesystem or reflective escape mechanisms, and malformed patches, exceptions, invalid trees, unequal results, timeouts, or executable-plan failures receive zero.

## Data / workload design

The evaluator uses real Stats-CEB data derived from Stack Overflow rather than generated fixtures: eight lowercase Zstandard-compressed Parquet relations containing 1,029,842 rows and 16,552,313 bytes. Plans come from the reproducibility artifact for a 2025 PVLDB paper and retain optimizer-produced aliases, filters, projections, equivalence classes, and estimated cardinalities. The solver substrate is a deliberately reduced planner slice, while the judge retains the upstream parser, conversion and lowering programs, reproduced execution binary, artifact timing records, and the authors’ cost-based policy as the comparison method.

Development and graded evaluation use disjoint, fixed twelve-query suites. Each contains two four-relation, two five-relation, seven six-relation, and one seven-relation acyclic equijoin plan. All initial plans violate the lowering invariant, so the identity stub cannot pass. Each candidate is first run through a one-repetition correctness pass containing the original binary plan, comparison plan, and candidate plan. A separate timing pass executes the two lowered methods in both ordering positions for seven repetitions, yielding fourteen observations per method and query.

This workload directly exercises the paper contribution: tree reassociation changes multisemijoin schedules and engine behavior on genuine data. It is nevertheless a compact fixed corpus and a pruned repository rather than the intact upstream build, so it remains possible to overfit broad Stats-CEB characteristics despite the hidden suite and 25-submission limit.

## Evaluation metrics

For each query \(q\), the calibrated artifact gain is

\[
A_q =
\frac{\operatorname{median}(\text{recorded BinaryJoin durations})}
     {\operatorname{median}(\text{recorded two-phase durations})}.
\]

If candidate and comparison JSON are byte-identical, \(R_q=1\) exactly. Otherwise,

\[
R_q =
\frac{\operatorname{median}(\text{live comparison durations})}
     {\operatorname{median}(\text{live candidate durations})}.
\]

The aggregate gain and score are

\[
G = \exp\left(\frac{1}{12}\sum_q
\log\left(\max(10^{-12}, A_qR_q)\right)\right),
\]

\[
\text{raw score}=\min(100,\max(0,100G/(1+G))),
\qquad
\text{score}=\operatorname{round}(\text{raw score}).
\]

Python’s ties-to-even rounding is used. The geometric mean prevents a policy from compensating arbitrarily poor cases with a single large win, while the \(10^{-12}\) floor avoids undefined logarithms. Symmetric execution order, fourteen-sample medians, integer reporting, and the exact byte-identity shortcut reduce warm-up, cache, and timing noise.

Performance scoring is unreachable unless the patch policy passes, only the allowed file changes, every tree invariant holds, lowering succeeds, all processes finish within their limits, and all query outputs agree exactly. Development and final query IDs are disjoint, limiting direct feedback-based memorization. Residual risks are the fixed and relatively small workload, roughly one-point timing-boundary movement for nonidentical plans, dependence on the bundled native executable and host environment, and the hard zero gate providing little distinction between a hidden structural edge case, an engine rejection, and a result mismatch.

## Agent execution performance

| Round | Trial | Agent | Reward / score | `beats_reference` | Margin | Cost |
|---:|---:|---|---:|---:|---:|---:|
| 1 | 0 | codex (`gpt-5.6-sol`) | 0.5373 / 53.7328 | 1 | +0.4595 | $6.82 |
| 2 | 0 | codex (`gpt-5.6-sol`) | 0 / 0 | 0 | -62.0000 | $13.13 |
| 2 | 1 | codex (`gpt-5.6-sol`) | 0 / 0 | 0 | -62.0000 | $16.60 |
| 2 | 2 | codex (`gpt-5.6-sol`) | 0 / 0 | 0 | -62.0000 | $13.36 |
| 3 | 0 | codex (`gpt-5.6-sol`) | 0 / 0 | 0 | -62.0000 | $10.42 |
| 3 | 1 | codex (`gpt-5.6-sol`) | 0 / 0 | 0 | -62.0000 | $11.32 |
| 3 | 2 | codex (`gpt-5.6-sol`) | 0 / 0 | 0 | -62.0000 | $12.82 |

Only one of seven graded trials beat the source-derived reference, and that occurred in round 1 before the workload expansion and answer-retrieval hardening; its margin was a narrow 0.4595 points. In rounds 2 and 3, agents used 15–25 successful development submissions and reached development scores around 67–71 or 68–69, often above the development reference, but all six selected policies failed the disjoint final suite’s execution/correctness gate and scored zero against a reference score of 62. The authors’ method is therefore a meaningful robustness and generalization bar rather than a strawman. The result also indicates that the present frontier is dominated by producing a universally legal executable tree, not merely by extracting another small latency improvement.

## Audit history

- **Round 1 — `revise`.** The auditor found no reward hacking: the agent changed only the allowed planner file and implemented genuine tree repair and cardinality-aware costing. However, each suite contained only four queries, the task allowed 100 submissions, and the statement exposed the exact paper title and searchable upstream contribution identifiers. The agent quickly recovered the paper recurrence and then tuned relation-specific heuristics over 28 submissions. Repeated identical patches also varied by several tenths of a point. In response, the task adopted the neutral `rewrite_policy.py::rewrite_plan` interface, removed direct bibliographic and source-path lookup clues, expanded each suite to twelve plans with matched 4/5/6/7-way coverage, increased paired timing repetitions to seven, separated correctness from timing, reduced the submission budget to 25, and changed reporting to whole points.

- **Round 2 — `accept`.** Three agents made legitimate one-file submissions and achieved strong development scores, but none passed the disjoint final gate. The auditor independently confirmed that a distinct non-reference policy could execute all final cases and score above the reference, ruling out a broken final suite. Workload size, suite composition, evaluator selection, submission workflow, and scoring constants were verified. The only suggested polish was to separate output inequality from other executable-plan failures without revealing query-specific information.

- **Round 3 — `accept`.** The diagnostic was split into query-neutral output-equality rejection and other executable-plan rejection. Three further agents again implemented genuine rooting and tree-repair strategies, reached valid development scores, and failed only on the hidden final executable-plan/correctness gate. The auditor found no hidden-data access, evaluator manipulation, hardcoded graded outputs, or policy bypass. The real workload, disjoint suite split, reference repeatability, and functioning Git/submission workflow were reconfirmed; no further revision was required.

## Recommendation for human review

**Ship with changes.** The task is scientifically grounded, uses real artifact plans and data, has strong correctness guardrails, and presents a difficult, unsaturated generalization frontier. Before merging, a human should verify these three points:

1. **Run the exact packaged solver workflow end to end.** Confirm that `/app` is a Git checkout, `make_submission.sh` and the injected or shipped `submit.sh` exist, and both an ordinary valid policy and the reference patch score successfully when submitted only through the documented commands.
2. **Reconcile calibration text with the final files and reports.** In particular, inspect the shipped stub for the claimed forbidden `__future__` import and remove or correct that statement if the import is absent. Also confirm that current reference scores are 65 on development and 62 on final, rather than stale pre-refinement values appearing in older audit evidence.
3. **Inspect hidden-gate failures and portability.** Manually classify the six final zeroes as structural, lowering, engine, timeout, or output-equality failures; verify that the query-neutral diagnostics remain accurate; and rerun the native executor/reference preflight on the intended production runtime to ensure the bundled binary and timing calibration remain valid.