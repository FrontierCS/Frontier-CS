# cand_002 — Final Review Dossier

## Problem statement

Solvers must implement `BudgetedDemandSearch.Find` in the supplied, buildable C# MetaOpt subtree. For each fully disclosed traffic-engineering instance, the method returns one demand-level index for each of 27 eligible source-destination pairs. The objective is to find a sparse traffic matrix maximizing the throughput gap between optimal path-form traffic engineering and the better of two production heuristics: fixed-partition POP and demand pinning.

Each demand index selects from `[0, 6, 18]`; at most nine demands may be nonzero. Positive demands of at most 6 are pinned to their first path, and their aggregate edge loads must remain capacity-feasible. The instance also discloses directed edges, capacities, up to four paths per pair, POP partitions, and optional three-pair search blocks.

The supplied `IGapOracle` permits at most 256 successful evaluations, while invalid and repeated-query behavior is explicitly defined. Solvers may instead or additionally construct local LP or optimization models from the disclosed instance; such work is constrained by the 30-second process deadline rather than the oracle-call budget. The project must build within 240 seconds, and malformed, infeasible, crashing, timed-out, or digest-invalid submissions score zero.

## Data / workload design

Revision 3 uses two disjoint suites of fifteen instances: a development suite used for iterative aggregate feedback and a held-out final suite used once for final verification. Each suite contains five private-keyed capacity perturbations for each of three exact directed topology skeletons from MetaOpt materials: `Topologies/swan.json`, `abilene.json`, and `b4-teavar.json`. Capacities lie between 24 and 36, while pair selection, POP assignments, block construction, perturbations, and frozen suite keys are benchmark-controlled.

Every instance has 27 eligible pairs, nine disclosed three-pair blocks, three POP partitions, up to four paths per pair, and a density limit of nine. The workload is grounded directly in MetaOpt’s traffic-engineering implementation and formulations, particularly `PopEncoder`, `DirectDemandPinningEncoder`, `TECombineHeuristicsEncoder`, and the unclustered primal-dual adversarial formulation represented by `TEAdversarialInputGenerator.MaximizeOptimalityGap`.

Calibration shows a meaningful strategy ladder on the development suite: zero-demand/naive search has mean gap 0, 256 sparse random samples reach 8.3111, the former clustered paper procedure reaches 11.5333, the six-work-unit joint reference reaches 25.6000, and the same formulation with 24 work units reaches 28.2444. Reviewer-only diagnostics found reasonably balanced topology means and no case contributing more than 9.4% of the reference total. The principal residual workload risk is structural breadth: thirty cases are still derived from only three topology skeletons, so future revisions should rotate both private keys and suites rather than repeatedly tuning the current set.

## Evaluation metrics

For each returned matrix, the judge independently solves exact path-form fractional multicommodity-flow LPs:

- `OPT(d)` uses full edge capacities.
- `POP(d)` independently optimizes each fixed partition using one third of every edge capacity and sums the three throughputs.
- `DP(d)` carries demands of at most 6 on their first paths, subtracts that load, and optimizes demand above 6 over the remaining path catalogs.
- `COMBINED(d) = max(POP(d), DP(d))`.
- The raw gap is `OPT(d) - COMBINED(d)`.

If \(G\) is the arithmetic mean raw gap over the applicable fifteen-instance suite, the bounded score is:

```text
score = 100 * (1 - exp(-G / 40))
```

clipped to `[0, 100]`, while `score_unbounded` reports \(G\). Success requires the candidate score to equal or exceed the paired role-specific global-reference score. The current reference is a deterministic six-work-unit, four-thread execution of MetaOpt’s unclustered joint primal-dual MILP, followed by one oracle validation; it does not add random search, annealing, swaps, or repair.

Anti-gaming controls include exact replay that ignores claimed objective values, locked-file digests, exclusion of Harbor-owned workflow files from the build copy, submission size and file-count limits, rejection of symlinks, fresh unprivileged processes, private held-out keys, process-group cleanup, and final reference computation outside the candidate-visible environment. Local LP replication is intentionally allowed equally to candidates and the reference, so the 256-query limit is a service budget rather than an information barrier. Remaining risks are development-suite overfitting through repeated aggregate feedback, dependence on a small number of topology families, and operational dependence on the bundled restricted-size Gurobi license used by the reference.

## Agent execution performance

| Round | Trial | Agent | Reward / score | `beats_reference` | Margin | Cost |
|---:|---:|---|---:|---:|---:|---:|
| 1 | 0 | codex (`gpt-5.6-sol`) | 0.000000 / 0.000000 | — | — | $2.8846 |
| 2 | 0 | codex (`gpt-5.6-sol`) | 0.512300 / 51.230036 | 1 | +27.929323 | $7.4194 |
| 2 | 1 | codex (`gpt-5.6-sol`) | 0.511962 / 51.196156 | 1 | +27.895443 | $3.6157 |
| 4 | 0 | codex (`gpt-5.6-sol`) | 0.498424 / 49.842393 | 1 | +1.527527 | $4.0540 |
| 4 | 1 | codex (`gpt-5.6-sol`) | 0.484869 / 48.486864 | 1 | +0.171997 | $8.2160 |
| 4 | 2 | codex (`gpt-5.6-sol`) | 0.508902 / 50.890177 | 1 | +2.575310 | $12.9539 |

Round 1 never reached candidate execution because of a substrate-digest integration defect. In round 2, both executable trials beat the then-current clustered reference by roughly 28 score points, demonstrating that it was a strawman relative to unrestricted global search. After replacement with the stronger joint MetaOpt reference and introduction of a disjoint final suite, all three round-4 trials still beat the source-aligned method, but only by 0.1720 to 2.5753 points. Their held-out scores ranged from 48.4869 to 50.8902 against a 48.3149 reference, while numerous development submissions remained below the reference. Thus the final reference is reachable but demanding and provides a real frontier rather than a nominal pass condition.

## Audit history

**Round 1 — revise.** All nine submissions were rejected before build with `locked substrate file changed`, producing no usable evidence about optimization quality or metric discrimination. The auditor found no reward hacking, but correctly treated the binary success signal as broken. Refinement traced the issue to eleven Harbor-injected root workflow files, excluded only those adapter-owned paths from the project digest and build copy, recomputed the digest, and added archive/extract CI tests proving that the starter and permitted edits pass while locked-file tampering fails. A scored C# integration smoke was also added.

**Round 2 — revise.** The repaired evaluator produced stable, nonzero scores, and exact replay showed no gaming. However, both trials beat the clustered reference by approximately 28 points; even early capable submissions exceeded it substantially. The auditor also flagged the small fixed suite, repeated tuning against the same cases, lack of held-out separation, and ambiguity over whether local LP replication was intended.

In response, the benchmark replaced the clustered gate with the faithful unclustered joint primal-dual MetaOpt MILP, retained the clustered method only as a baseline, and calibrated the new reference solely on development data. The workload expanded to disjoint fifteen-case development and final suites with private keyed generation. Local LP evaluation was explicitly permitted to both candidates and the reference. Reviewer-only per-case and per-topology balance diagnostics were added, and candidate execution was hardened through privilege dropping, resource limits, root-only judge data, fail-closed role handling, and process-group cleanup.

**Round 3 — packaging repair.** A pre-trial judge-image failure revealed that the adapter invoked `pip3` without installing it. `python3-pip` was added to the declared judge packages, and the exact installation path was replayed on the target .NET SDK image with NumPy, SciPy, and pinned `gurobipy==13.0.0`. Structural smoke tests and the reference replay then succeeded without changing suites, objectives, calibration, or the success gate. The earlier stage-3 LLM review’s concerns about missing preflight evidence, a six-case suite, and the old clustered reference were therefore superseded by these later refinements.

**Round 4 — accept.** Three independent agents completed the held-out evaluation and all beat the strengthened reference by modest, differentiated margins. The auditor found no reward hacking, judged the workload suitable, the exact metric operational and discriminative, and the reference well calibrated. Final scores had a standard deviation of approximately 0.984 and a maximum pairwise spread of 2.403 points, showing both reproducibility and meaningful ranking signal. The trace auditor recommended no further refinement.

## Recommendation for human review

**Ship.** The initial infrastructure defect and weak reference were both materially corrected, and the final real-agent audit supports validity, difficulty, generalization, and discrimination.

Before merging, a human maintainer should verify these three items by hand:

1. **Reproduce the submission-boundary tests:** confirm that the exact Harbor copy/archive path accepts an untouched starter and allowed `BudgetedDemandSearch.cs`/`Candidate/*.cs` edits, while rejecting a modified locked file or symlink.
2. **Reproduce one complete held-out evaluation:** verify exact LP replay, per-instance timeouts, unprivileged execution, process cleanup, and the reported final reference score of `48.31486655083007`.
3. **Validate long-term private dependencies:** ensure the development and final suite keys remain inaccessible to candidates, archive the frozen suite-generation procedure, and confirm that the pinned Gurobi package and bundled restricted license remain valid before deployment.