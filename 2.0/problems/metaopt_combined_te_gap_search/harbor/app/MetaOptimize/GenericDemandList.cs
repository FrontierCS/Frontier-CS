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
    public class GenericDemandList : IDemandList
    {
        /// <summary>
        /// demand quantization lvls.
        /// </summary>
        public ISet<double> demandList;

        /// <summary>
        /// class constructor function.
        /// </summary>
        public GenericDemandList(ISet<double> demandList)
        {
            this.demandList = demandList;
        }

        /// <summary>
        /// The demand list used for an specific pair.
        /// </summary>
        public ISet<double> GetDemandsForPair(string src, string dst) {
            return this.demandList;
        }

        /// <summary>
        /// get random non-zero demand between specific pair.
        /// </summary>
        public double GetRandomNonZeroDemandForPair(Random rng, string src, string dst) {
            var demandlvls = new HashSet<double>(this.GetDemandsForPair(src, dst));
            demandlvls.Remove(0);
            var demand = demandlvls.ToList()[rng.Next(demandlvls.Count())];
            return demand;
        }

        /// <summary>
        /// get random demand between specific pair.
        /// </summary>
        public double GetRandomDemandForPair(Random rng, string src, string dst) {
            var demandlvls = new HashSet<double>(this.GetDemandsForPair(src, dst));
            demandlvls.Add(0);
            var demand = demandlvls.ToList()[rng.Next(demandlvls.Count())];
            return demand;
        }
    }
}