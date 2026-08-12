namespace MetaOptimize
{
    using System.Collections.Generic;
    /// <summary>
    /// interface for TE optimization solution.
    /// </summary>
    public class TEOptimizationSolution : OptimizationSolution
    {
        /// <summary>
        /// The demands for the problem.
        /// </summary>
        public IDictionary<(string, string), double> Demands { get; set; }

        /// <summary>
        /// The flow path allocation for the problem.
        /// </summary>
        public IDictionary<string[], double> FlowsPaths { get; set; }

        /// <summary>
        /// The objective by the optimization.
        /// </summary>
        public double MaxObjective { get; set; }
    }
}