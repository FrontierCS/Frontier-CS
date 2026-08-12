// <copyright file="OptimizationEncoding.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System.Collections.Generic;

    /// <summary>
    /// The encoding of an optimization.
    /// </summary>
    public class OptimizationEncoding<TVar, TSolution>
    {
        /// <summary>
        /// The global objective.
        /// </summary>
        public TVar GlobalObjective { get; set; }

        /// <summary>
        /// The maximization objective.
        /// </summary>
        public Polynomial<TVar> MaximizationObjective { get; set; }
    }
}
