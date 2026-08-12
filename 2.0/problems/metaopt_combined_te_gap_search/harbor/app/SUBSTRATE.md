# MetaOpt search substrate

This is a pruned, buildable subtree of Microsoft MetaOpt. The original solver
interfaces and traffic-engineering encoders remain in `MetaOptimize/`; unrelated
Raha failure analysis, PIFO, vector-bin-packing algorithms, CLI, and test code
is omitted. One shared `Bins` data type remains because the upstream generic
encoder interface names it.

Edit `MetaOptimize/TrafficEngineering/BudgetedDemandSearch.cs`. You may add C#
helpers below `MetaOptimize/TrafficEngineering/Candidate/`. The locked challenge
runner exposes exact POP, demand-pinning, and optimal path-form replay through
`IGapOracle`. Build with:

```bash
dotnet build MetaOptimize.Challenge/MetaOptimize.Challenge.csproj -c Release
```
