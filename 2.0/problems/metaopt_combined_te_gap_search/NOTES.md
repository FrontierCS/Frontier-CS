# Reviewer notes
Task classification: Type A — beat the upstream implementation; the solver's stronger search is not in the repository.
The paired reference implements the joint model of `MaximizeOptimalityGap` in `MetaOptimize/TrafficEngineering/TEAdversarialInputGenerator.cs`.
It uses MetaOpt's primal/dual inner rewrite with all 27 demand variables jointly open and the paper's Gurobi backend under a deterministic six-work-unit limit; there is no generic post-search.
The former reference, `RandomlyInitializeDemands` plus `MaximizeOptimalityGapWithClusteringV2`, remains `baseline_clustered.py` and is no longer the gate.
POP splitting and maximum-of-heuristics are grounded in `PopEncoder.Encoding` and `TECombineHeuristicsEncoder.Encoding`.
Threshold pinning and residual capacity are grounded in `DirectDemandPinningEncoder.InitializeVariables` and `Encoding`.
SWAN, Abilene, and B4 skeletons come verbatim from `Topologies/swan.json`, `abilene.json`, and `b4-teavar.json`.
Levels `[0,6,18]`, capacities 24–36, 27 pairs, nine nonzeros, four paths, three partitions, and score scale 40 are challenge constants (not from materials).
Revision 3's disjoint 15-case development/final suites and private frozen keyed seeds are challenge constants (not from materials).
The 256 oracle calls, 240-second build, 30-second case limit, 30 submissions, resources, and `1e-7` tolerance are challenge constants (not from materials).
Candidates and reference may build local LP models from each fully disclosed instance; 256 limits only calls to the supplied oracle.
Directory submission fits the real multi-file .NET project; editable source and `Candidate/*.cs` are the only project exceptions.
Digest-v2 locking, Harbor-wrapper stripping, unprivileged execution, and a root-only `/judge` directory protect evaluator and seed material.
Reviewer-only diagnostics retain per-case gaps and topology means but the API reports no case, topology, matrix, path, or seed details.
Development calibration: naive 0.000000; random 18.761245; clustered 25.048829; global reference 47.270758; extended global 50.644013.
Held-out audit: reference 48.314867; extended global 50.726205; reference largest-case shares are 9.38% dev and 9.09% final.
Per `GOAL.md` this targets MetaOpt TE scaffolding; candidates have the pruned .NET/OR-Tools project and the judge pins Gurobi 13 for the restricted-size paper reference plus SciPy/HiGHS for exact replay.
## Leak inventory
Omitted as answer-bearing/unrelated: `TEAdversarialInputGenerator.cs`, `AdversarialInputSimplifier.cs`, failure analysis, PIFO/VBP, CLI/tests, and upstream results/docs.

## Shipped scaffolding audit

The filenames flagged by the structural audit are required locked scaffolding,
not implementations of `BudgetedDemandSearch.Find`:

- `ReplayOracle.cs` is the challenge harness that validates and replays a
  candidate matrix. It does not search for or return a matrix.
- `OptimizationSolution.cs`, `TEOptimizationSolution.cs`, and
  `TEMaxFlowOptimizationSolution.cs` are result/data containers required by the
  retained MetaOpt interfaces.
- `TEMaxFlowOptimalEncoder.cs` is the inner path-flow encoder used to define the
  comparison objective; it contains no adversarial demand search.
- `ExpectedPopEncoder.cs` is a locked upstream POP encoder retained so the
  pruned MetaOpt subtree remains coherent; it is not used as the submitted
  search implementation or the success-gate reference.

The actual source-work adversarial generator remains omitted, and the only
editable search entry point is `BudgetedDemandSearch.cs`.
