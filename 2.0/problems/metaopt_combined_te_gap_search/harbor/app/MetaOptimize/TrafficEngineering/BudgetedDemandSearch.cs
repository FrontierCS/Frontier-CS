namespace MetaOptimize;

/// <summary>
/// Editable bounded search for a demand matrix with a large exact TE gap.
/// </summary>
public static class BudgetedDemandSearch
{
    /// <summary>
    /// Return one level index per eligible demand pair.
    /// </summary>
    public static int[] Find(AdversarialSearchInstance instance, IGapOracle oracle)
    {
        // Starter policy: put the largest level on the first density-limited pairs.
        var answer = new int[instance.Pairs.Length];
        var largest = instance.Levels.Length - 1;
        for (var pairIndex = 0;
             pairIndex < instance.DensityLimit && pairIndex < answer.Length;
             pairIndex++)
        {
            answer[pairIndex] = largest;
        }

        return answer;
    }
}
