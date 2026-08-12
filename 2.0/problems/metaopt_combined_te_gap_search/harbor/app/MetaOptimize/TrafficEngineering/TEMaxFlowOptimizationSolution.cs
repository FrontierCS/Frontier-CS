// <copyright file="OptimizationSolution.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System.Collections.Generic;

    /// <summary>
    /// A solution to an optimization problem.
    /// </summary>
    public class TEMaxFlowOptimizationSolution : TEOptimizationSolution
    {
        /// <summary>
        /// The flow allocation for the problem.
        /// </summary>
        public IDictionary<(string, string), double> Flows { get; set; }

        /// <summary>
        /// Each sample total demand.
        /// </summary>
        public IList<double> TotalDemmandMetSample = null;
    }
}
