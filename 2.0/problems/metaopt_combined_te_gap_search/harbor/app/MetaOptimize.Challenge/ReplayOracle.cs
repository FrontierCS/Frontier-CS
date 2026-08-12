#pragma warning disable SA1010

namespace MetaOptimize.Challenge;

using System;
using System.Collections.Generic;
using System.Linq;
using Google.OrTools.LinearSolver;

internal sealed class ReplayOracle : IGapOracle
{
    private const double Tolerance = 1e-7;
    private readonly AdversarialSearchInstance instance;

    internal ReplayOracle(AdversarialSearchInstance instance)
    {
        this.instance = instance;
    }

    public int QueriesUsed { get; private set; }

    public int QueryBudget => this.instance.QueryBudget;

    public GapEvaluation Evaluate(IReadOnlyList<int> demandLevelIndices)
    {
        if (this.QueriesUsed >= this.QueryBudget)
        {
            throw new InvalidOperationException("oracle query budget exceeded");
        }

        var demands = this.Validate(demandLevelIndices);
        this.QueriesUsed++;
        var optimal = this.Solve(demands, Enumerable.Range(0, demands.Length), 1.0, null);
        var pop = 0.0;
        for (var partition = 0; partition < this.instance.PopPartitions; partition++)
        {
            var selected = Enumerable.Range(0, demands.Length)
                .Where(index => this.instance.Pairs[index].Partition == partition);
            pop += this.Solve(demands, selected, 1.0 / this.instance.PopPartitions, null);
        }

        var remaining = this.instance.Edges.Select(edge => edge.Capacity).ToArray();
        var pinned = 0.0;
        var largePairs = new List<int>();
        for (var index = 0; index < demands.Length; index++)
        {
            var demand = demands[index];
            if (demand <= 0.0)
            {
                continue;
            }

            if (demand <= this.instance.PinningThreshold + Tolerance)
            {
                pinned += demand;
                foreach (var edgeIndex in this.instance.Pairs[index].Paths[0])
                {
                    remaining[edgeIndex] -= demand;
                }
            }
            else
            {
                largePairs.Add(index);
            }
        }

        var pinning = remaining.Any(capacity => capacity < -Tolerance)
            ? 0.0
            : pinned + this.Solve(demands, largePairs, 1.0, remaining.Select(value => Math.Max(0.0, value)).ToArray());
        var gap = Math.Max(0.0, optimal - Math.Max(pop, pinning));
        return new GapEvaluation(gap, optimal, pop, pinning);
    }

    internal double[] Validate(IReadOnlyList<int> demandLevelIndices)
    {
        if (demandLevelIndices is null || demandLevelIndices.Count != this.instance.Pairs.Length)
        {
            throw new ArgumentException("wrong demand vector length");
        }

        var demands = new double[demandLevelIndices.Count];
        var nonzero = 0;
        for (var index = 0; index < demandLevelIndices.Count; index++)
        {
            var level = demandLevelIndices[index];
            if (level < 0 || level >= this.instance.Levels.Length)
            {
                throw new ArgumentException("demand level index outside range");
            }

            demands[index] = this.instance.Levels[level];
            if (demands[index] > 0.0)
            {
                nonzero++;
            }
        }

        if (nonzero > this.instance.DensityLimit)
        {
            throw new ArgumentException("demand density limit exceeded");
        }

        var pinnedLoad = new double[this.instance.Edges.Length];
        for (var pairIndex = 0; pairIndex < demands.Length; pairIndex++)
        {
            var demand = demands[pairIndex];
            if (demand <= 0.0 || demand > this.instance.PinningThreshold + Tolerance)
            {
                continue;
            }

            foreach (var edgeIndex in this.instance.Pairs[pairIndex].Paths[0])
            {
                pinnedLoad[edgeIndex] += demand;
            }
        }

        for (var edgeIndex = 0; edgeIndex < pinnedLoad.Length; edgeIndex++)
        {
            if (pinnedLoad[edgeIndex] > this.instance.Edges[edgeIndex].Capacity + Tolerance)
            {
                throw new ArgumentException("pinned shortest-path load exceeds capacity");
            }
        }

        return demands;
    }

    private double Solve(
        IReadOnlyList<double> demands,
        IEnumerable<int> selectedPairs,
        double capacityScale,
        IReadOnlyList<double> capacityOverride)
    {
        using var solver = Solver.CreateSolver("GLOP")
            ?? throw new InvalidOperationException("GLOP is unavailable");
        var edgeConstraints = new Constraint[this.instance.Edges.Length];
        for (var edgeIndex = 0; edgeIndex < edgeConstraints.Length; edgeIndex++)
        {
            var capacity = capacityOverride is null
                ? this.instance.Edges[edgeIndex].Capacity * capacityScale
                : Math.Max(0.0, capacityOverride[edgeIndex]);
            edgeConstraints[edgeIndex] = solver.MakeConstraint(0.0, capacity);
        }

        var objective = solver.Objective();
        foreach (var pairIndex in selectedPairs)
        {
            if (demands[pairIndex] <= 0.0)
            {
                continue;
            }

            var demandConstraint = solver.MakeConstraint(0.0, demands[pairIndex]);
            var paths = this.instance.Pairs[pairIndex].Paths;
            for (var pathIndex = 0; pathIndex < paths.Length; pathIndex++)
            {
                var variable = solver.MakeNumVar(0.0, demands[pairIndex], $"f_{pairIndex}_{pathIndex}");
                demandConstraint.SetCoefficient(variable, 1.0);
                objective.SetCoefficient(variable, 1.0);
                foreach (var edgeIndex in paths[pathIndex])
                {
                    edgeConstraints[edgeIndex].SetCoefficient(variable, 1.0);
                }
            }
        }

        objective.SetMaximization();
        var status = solver.Solve();
        if (status is not Solver.ResultStatus.OPTIMAL and not Solver.ResultStatus.FEASIBLE)
        {
            throw new InvalidOperationException("traffic replay LP failed");
        }

        return objective.Value();
    }
}
