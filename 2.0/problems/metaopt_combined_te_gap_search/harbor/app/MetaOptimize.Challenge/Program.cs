#pragma warning disable SA1010

namespace MetaOptimize.Challenge;

using System;
using System.IO;
using System.Text.Json;

internal static class Program
{
    private sealed class RunnerResult
    {
        public int[] Levels { get; set; } = [];

        public int Queries { get; set; }
    }

    public static int Main()
    {
        var realOutput = Console.Out;
        try
        {
            var instance = JsonSerializer.Deserialize<AdversarialSearchInstance>(Console.In.ReadToEnd())
                ?? throw new InvalidDataException("missing instance");
            var oracle = new ReplayOracle(instance);
            Console.SetOut(TextWriter.Null);
            Console.SetError(TextWriter.Null);
            var levels = BudgetedDemandSearch.Find(instance, oracle);
            oracle.Validate(levels);
            Console.SetOut(realOutput);
            Console.WriteLine(JsonSerializer.Serialize(new RunnerResult
            {
                Levels = levels,
                Queries = oracle.QueriesUsed,
            }, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower }));
            return 0;
        }
        catch
        {
            Console.SetOut(realOutput);
            Console.WriteLine("{\"error\":\"search failed\"}");
            return 1;
        }
    }
}
