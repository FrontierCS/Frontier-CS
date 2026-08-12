## Task

`metaopt_combined_te_gap_search` asks solvers to implement a bounded C# search for sparse traffic matrices maximizing `OPT - max(POP, DP)`, with every final matrix independently replayed. It is built on MetaOpt's `PopEncoder`, `DirectDemandPinningEncoder`, `TECombineHeuristicsEncoder`, and the joint primal-dual adversarial formulation in `TEAdversarialInputGenerator.MaximizeOptimalityGap`; the real pruned .NET project is the editable substrate.

## Why this is a real task

There are 27 ternary demands, at most nine active, and interacting POP, pinning, path, and capacity effects. The revision-3 development ladder is well spread: starter/naive 0.000000 (mean gap 0.000000), 256 sparse random samples 18.761245 (8.311111), the former clustered paper method 25.048829 (11.533333), the six-work-unit joint global reference 47.270758 (25.600000), and the same paper formulation at 24 work units 50.644013 (28.244444). Round-2 agents progressed through 46.03 before reaching 50.5+, so the new bar is above an early capable result but remains beatable; it is not a theoretical optimum or score ceiling.

## Data / workload design

Revision 3 has disjoint development and final suites, each containing fifteen cases: five private-keyed perturbations on each exact SWAN, Abilene, and B4 directed skeleton. Iterative submissions receive only aggregate development feedback; the final role switches once to the held-out suite. Each disclosed instance still has 27 pairs, levels `[0,6,18]`, at most nine nonzeros, up to four paths per pair, three POP partitions, and 256 supplied-oracle calls. The keyed seed material, dimensions, and split are challenge constants (not from materials), frozen before calibration and kept in the root-only judge.

## Scoring

The judge independently solves path-form LPs for `OPT`, one-third-capacity partitioned `POP`, and residual-capacity `DP`. With `G` the applicable suite's mean gap, `score = 100 * (1 - exp(-G / 40))`, clipped to `[0,100]`, while the unbounded score is `G`; 40 is a challenge constant (not from materials). `beats_reference = 1` exactly when candidate score is at least the paired role-specific global-reference score, with `reference_score` and `margin` returned. Claims are ignored, locked files are hashed, runtime code is unprivileged, and local LP modeling is explicitly allowed for both candidate and reference; 256 limits only supplied-oracle calls.

## Known risks

Both suites still use only three topology skeletons, and strong searches may cluster within a few points even after perturbation expansion. No individual case dominates: reference largest-case shares are 9.38% on development and 9.09% on final. The global reference is an anytime implementation of MetaOpt's joint formulation under Gurobi's packaged restricted-size, non-production license, not a proof of the discrete optimum. Its model guard keeps every frozen case below the 2,000-variable and 2,000-constraint restricted-license caps. Future maintainers should rotate both private keys and suites together, refresh the pinned solver package before its bundled license window ends, and rerun balance diagnostics rather than tune cases by outcome.

## Changes made in refinement

- Revision 2 expanded the original six cases to twelve deterministic cases and authenticated relocated reviewer reference files.
- It established the historical ladder: naive 0.000000, random 20.480401, clustered reference 23.300713, and global swaps 37.072974.

## Round 1 fixes

- Diagnosed Harbor's eleven injected root workflow files as the cause of universal digest rejection and excluded only those exact adapter-owned paths from the project digest/build copy.
- Recomputed digest v2 and added Harbor archive/extract CI proving starter and allowed edits build while locked-file tampering fails.
- Added a scored C# integration smoke, which made candidate execution and frontier metrics operational.

## Round 2 fixes

- Replaced the under-calibrated clustered success gate with a faithful, unclustered `MaximizeOptimalityGap` primal-dual MILP using the paper's Gurobi backend. The gate contains no generic random/annealing/swap/repair augmentation: it is a deterministic six-work-unit solve plus one oracle validation. The development reference rose from clustered 25.048829 to 47.270758, while clustered-V2 remains a reported baseline.
- Calibrated only on the separate development suite: naive 0.000000, random 18.761245, clustered 25.048829, global reference 47.270758, and the same global formulation at 24 work units 50.644013. The untouched final audit preserves headroom at 48.314867 versus 50.726205. This deliberately clears the early capable 46.03 stage without targeting a zero margin or a known optimum.
- Expanded from twelve feedback cases to two disjoint 15-case suites. Development submissions never score on the final suite, and private keyed seed material replaces the public revision-2 derivation.
- Added reviewer-only per-case and per-topology diagnostics. Reference topology means are 24.0/26.2/26.6 on development and 26.4/22.2/30.6 on final; largest-case shares stay below 9.4%. These diagnostics are not returned to candidates.
- Clarified that local LP replication is allowed and gave the global reference that same capability; the 256 budget constrains only calls to `IGapOracle`, while the 30-second process deadline constrains local computation.
- Hardened private data and execution: production reference results remain in parent memory only, final reference computation occurs after candidate execution, unknown submission roles fail closed, C# cases drop to uid/gid 65534 with process/file-descriptor/core limits, surviving process-group helpers are killed between cases, and `/judge` becomes root-only before submissions run. The CPU rlimit now permits the documented four CPUs for the full wall deadline instead of accidentally charging four-threaded candidates four times faster.

## Round 3 fixes

- Fixed the pre-trial judge-image build failure by declaring `python3-pip` in
  `runtime.judge_apt_packages`. The adapter invokes `pip3` whenever
  `judge_pip_packages` is nonempty, but its minimal judge template does not
  otherwise install pip.
- Replayed the adapter's exact package-install command on
  `mcr.microsoft.com/dotnet/sdk:8.0-bookworm-slim`; NumPy, SciPy, and pinned
  `gurobipy==13.0.0` now install successfully instead of exiting with code 127.
- Re-ran both evaluator modes: the dependency-free structural smoke returns a
  valid nonnegative score, and the declared-dependency reference replay remains
  47.270758 (mean gap 25.600000). No suite, objective, success gate, reference
  work budget, or calibration value changed in this packaging-only repair.
