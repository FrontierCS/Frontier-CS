// <copyright file="Topology.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.Diagnostics;
    using System.Linq;

    /// <summary>
    /// A simple bin class that contains the bin sizes.
    /// </summary>
    public class Bins
    {
        private List<List<double>> binSizeList;

        /// <summary>
        /// Creates a new instance of the <see cref="Bins"/> class.
        /// Which captures the bins for VBP. If we want to assume all bins have
        /// the same size we can use this function to initiate the class:
        /// you only need to specify the
        /// number of bins and the size of each bin.
        /// </summary>
        public Bins(int numBins, List<double> binSize)
        {
            this.binSizeList = new List<List<double>>();
            for (int i = 0; i < numBins; i++) {
                this.binSizeList.Add(new List<double>(binSize));
            }
        }

        /// <summary>
        /// Creates a new instance of the <see cref="Bins"/> class.
        /// Use this function if the bins you want to use have different sizes.
        /// The input here will have to specify the size of each bin individually.
        /// </summary>
        public Bins(List<List<double>> binList)
        {
            this.binSizeList = new List<List<double>>();
            foreach (var binSize in binList) {
                this.binSizeList.Add(binSize.ToList());
            }
        }

        /// <summary>
        /// Get list of bin sizes.
        /// </summary>
        public ReadOnlyCollection<ReadOnlyCollection<double>> getBinSizes()
        {
            var binList = new List<ReadOnlyCollection<double>>();
            foreach (var binSize in this.binSizeList) {
                binList.Add(binSize.AsReadOnly());
            }
            return binList.AsReadOnly();
        }

        /// <summary>
        /// return number of bins.
        /// </summary>
        public int GetNum()
        {
            return this.binSizeList.Count;
        }

        /// <summary>
        /// return max capacity across all bins.
        /// </summary>
        public double MaxCapacity(int dim)
        {
            double maxCap = 0;
            foreach (var binSize in this.binSizeList) {
                maxCap = Math.Max(maxCap, binSize[dim]);
            }
            return maxCap;
        }

        /// <summary>
        /// return the sum of capacity of first $K$ bins.
        /// </summary>
        public double SumCapFirst(int k, int dim) {
            Debug.Assert(k <= this.binSizeList.Count);
            double sumCap = 0;
            for (int i = 0; i < k; i++) {
                sumCap += this.binSizeList[k][dim];
            }
            return sumCap;
        }

        /// <summary>
        /// return the sum of capaicty of bin $k$ over all dimensions.
        /// </summary>
        public double SumOverAllDim(int k) {
            double sumCap = 0;
            foreach (var binSize in this.binSizeList[k]) {
                sumCap += binSize;
            }
            return sumCap;
        }

        /// <summary>
        /// return the sum of capacity of first $k$ bins over all dimensions.
        /// </summary>
        public double SumOverAllDimFirst(int k) {
            Debug.Assert(k <= this.binSizeList.Count);
            double sumCap = 0;
            for (int i = 0; i < k; i++) {
                sumCap += this.SumOverAllDim(i);
            }
            return sumCap;
        }

        /// <summary>
        /// returns a new bin object consisting of the first $k$ bins from this one.
        /// </summary>
        public Bins GetFirstKBins(int k) {
            Debug.Assert(k <= this.binSizeList.Count);
            var newBinSizeList = new List<List<double>>();
            for (int i = 0; i < k; i++) {
                newBinSizeList.Add(this.binSizeList[k]);
            }
            return new Bins(newBinSizeList);
        }
    }
}