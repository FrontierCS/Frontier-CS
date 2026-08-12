// <copyright file="KktOptimizationGenerator.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    using System.Linq;

    /// <summary>
    /// A DemandList to specify demand Quantization lvls between every pair.
    /// </summary>
    public class GenericList : IList
    {
        /// <summary>
        /// demand quantization lvls.
        /// </summary>
        public ISet<double> List;

        /// <summary>
        /// class constructor function.
        /// </summary>
        public GenericList(ISet<double> inputList)
        {
            this.List = inputList;
        }

        /// <summary>
        /// The demand list used for an specific pair.
        /// </summary>
        public ISet<double> GetValueForPair(string src, string dst) {
            return this.List;
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

        /// <summary>
        /// get random demand between specific pair.
        /// </summary>
        public double GetRandomValueForPair(Random rng, string src, string dst) {
            var lvls = new HashSet<double>(this.GetValueForPair(src, dst));
            lvls.Add(0);
            var value = lvls.ToList()[rng.Next(lvls.Count())];
            return value;
        }
    }
}