// <copyright file="IEncoder.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

// TODO: should we change the name for this class and its function? It seems like it applies more broadly than just for traffic engineering.
namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    /// <summary>
    /// An interface for sepcifying demand list for Primal Dual Encoding.
    /// </summary>
    public interface IList
    {
        /// <summary>
        /// The demand list used for an specific pair.
        /// </summary>
        public ISet<double> GetValueForPair(string src, string dst);

        /// <summary>
        /// get random non-zero demand between specific pair.
        /// </summary>
        public double GetRandomNonZeroValueForPair(Random rng, string src, string dst);
    }
}
