#pragma warning disable CS1591, SA1010

namespace MetaOptimize;

using System.Collections.Generic;
using System.Text.Json.Serialization;

/// <summary>
/// One directed capacitated edge in a replay instance.
/// </summary>
public sealed class SearchEdge
{
    [JsonPropertyName("source")]
    public int Source { get; set; }

    [JsonPropertyName("target")]
    public int Target { get; set; }

    [JsonPropertyName("capacity")]
    public double Capacity { get; set; }
}

/// <summary>
/// One eligible source-destination demand and its path catalog.
/// </summary>
public sealed class SearchDemandPair
{
    [JsonPropertyName("source")]
    public int Source { get; set; }

    [JsonPropertyName("target")]
    public int Target { get; set; }

    [JsonPropertyName("partition")]
    public int Partition { get; set; }

    [JsonPropertyName("paths")]
    public int[][] Paths { get; set; } = [];
}

/// <summary>
/// A bounded adversarial traffic-engineering search instance.
/// </summary>
public sealed class AdversarialSearchInstance
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("node_count")]
    public int NodeCount { get; set; }

    [JsonPropertyName("edges")]
    public SearchEdge[] Edges { get; set; } = [];

    [JsonPropertyName("pairs")]
    public SearchDemandPair[] Pairs { get; set; } = [];

    [JsonPropertyName("levels")]
    public double[] Levels { get; set; } = [];

    [JsonPropertyName("density_limit")]
    public int DensityLimit { get; set; }

    [JsonPropertyName("pinning_threshold")]
    public double PinningThreshold { get; set; }

    [JsonPropertyName("pop_partitions")]
    public int PopPartitions { get; set; }

    [JsonPropertyName("query_budget")]
    public int QueryBudget { get; set; }

    [JsonPropertyName("search_blocks")]
    public int[][] SearchBlocks { get; set; } = [];
}

/// <summary>
/// Exact replay values for one demand matrix.
/// </summary>
public readonly record struct GapEvaluation(
    double Gap,
    double OptimalThroughput,
    double PopThroughput,
    double DemandPinningThroughput);

/// <summary>
/// Budgeted exact-replay interface exposed to the editable search strategy.
/// </summary>
public interface IGapOracle
{
    int QueriesUsed { get; }

    int QueryBudget { get; }

    GapEvaluation Evaluate(IReadOnlyList<int> demandLevelIndices);
}
