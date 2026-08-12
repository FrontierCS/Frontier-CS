// <copyright file="KktOptimizationGenerator.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using ZenLib;

    /// <summary>
    /// A DemandList to specify demand Quantization lvls between every pair.
    /// </summary>
    public class PairwiseDemandList : IList
    {
        /// <summary>
        /// demand quantization lvls.
        /// </summary>
        private IDictionary<(string, string), ISet<double>> demandList;

        /// <summary>
        /// class constructor function.
        /// </summary>
        public PairwiseDemandList(IDictionary<(string, string), ISet<double>> demandList)
        {
            this.demandList = demandList;
        }

        /// <summary>
        /// The demand list used for an specific pair.
        /// </summary>
        public ISet<double> GetValueForPair(string src, string dst) {
            return this.demandList[(src, dst)];
        }

        /// <summary>
        /// get random non-zero demand between specific pair.
        /// </summary>
        public double GetRandomNonZeroValueForPair(Random rng, string src, string dst) {
            var demandlvls = new HashSet<double>(this.GetValueForPair(src, dst));
            demandlvls.Remove(0);
            var demand = demandlvls.ToList()[rng.Next(demandlvls.Count())];
            return demand;
        }
    }
}