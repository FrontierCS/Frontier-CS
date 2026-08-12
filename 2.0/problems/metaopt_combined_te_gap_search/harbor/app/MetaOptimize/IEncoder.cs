// <copyright file="IEncoder.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System.Collections.Generic;
    /// <summary>
    /// An interface for an optimization encoder.
    /// </summary>
    /// TODO: we need a better comment here since this is one of the functions one would heavily use in order to
    /// write a new heuristic.
    public interface IEncoder<TVar, TSolution>
    {
        /// <summary>
        /// The solver used for the encoder.
        /// </summary>
        public ISolver<TVar, TSolution> Solver { get; set; }

        /// <summary>
        /// reset the heuristic.
        /// </summary>
        public void CleanAll()
        {
            throw new System.Exception("Not Implemented....");
        }
                /// <summary>
        /// This is the new version for both capplan and MLUfailure analysis.
        /// </summary>
        /// <returns></returns>
        /// <exception cref="System.Exception"></exception>
        public OptimizationEncoding<TVar, TSolution> Encoding(Topology topology,
                                                              bool modelFailures = true,
                                                              Dictionary<(string, string), Polynomial<TVar>> preDemandVariables = null,
                                                              Dictionary<(string, string), Polynomial<TVar>> preCapVariables = null,
                                                              Dictionary<string[], Polynomial<TVar>> prePathExtensionCapacities = null,
                                                              Dictionary<(string, string), double> demandEqualityConstraints = null,
                                                              Dictionary<(string, string), double> capacityEqualityConstraints = null,
                                                              Dictionary<string[], double> pathExtensionCapacityConstraints = null,
                                                              bool noAdditionalConstraints = false,
                                                              InnerRewriteMethodChoice innerRewriteMethod = InnerRewriteMethodChoice.KKT,
                                                              PathType pathType = PathType.KSP,
                                                              Dictionary<(string, string), string[][]> selectedPaths = null,
                                                              Dictionary<(int, string, string), double> historicDemandConstraints = null,
                                                              HashSet<string> excludeEdges = null,
                                                              int numProcesses = -1)
        {
            throw new System.Exception("MLU encoding missing");
        }
        /// <summary>
        /// The encoding for Africa V2.
        /// </summary>
        public OptimizationEncoding<TVar, TSolution> Encoding(Topology topology,
                                                              bool modelFailures = true,
                                                              Dictionary<(string, string), string[][]> primaryPaths = null,
                                                              Dictionary<(string, string), string[][]> backupPaths = null,
                                                              Dictionary<(string, string), Polynomial<TVar>> preDemandVariables = null,
                                                              Dictionary<(string, string), Polynomial<TVar>> preCapVariables = null,
                                                              Dictionary<string[], Polynomial<TVar>> prePathExtensionCapacities = null,
                                                              Dictionary<(string, string), double> demandEqualityConstraints = null,
                                                              Dictionary<(string, string), double> capacityEqualityConstraints = null,
                                                              Dictionary<string[], double> pathExtensionCapacityConstraints = null,
                                                              bool noAdditionalConstraints = false,
                                                              InnerRewriteMethodChoice innerRewriteMethodChoice = InnerRewriteMethodChoice.KKT,
                                                              PathType pathType = PathType.KSP,
                                                              Dictionary<(int, string, string), double> historicDemandConstraints = null,
                                                              HashSet<string> excludeNodesEdges = null,
                                                              int numProcesses = -1)
        {
            throw new System.Exception("Encoder for the split paths cut encoder.");
        }
        /// <summary>
        /// Encodes the capacity augmentation problem.
        /// </summary>
        public OptimizationEncoding<TVar, TSolution> Encoding(
            Topology topology,
            Dictionary<(string, string), double> demands = null,
            Dictionary<(string, string), double> flows = null,
            double targetDemandMet = -1,
            int minAugmentation = 0,
            Dictionary<(string, string), int> exclude = null,
            Dictionary<(string, string), string[][]> path = null,
            bool specialWeight = true,
            bool addOnExisting = false)
        {
            throw new System.Exception("Capacity Augmentation encoder not implemented");
        }
        /// <summary>
        /// TE max flow encoder.
        /// </summary>
        /// <returns></returns>
        public OptimizationEncoding<TVar, TSolution> Encoding(
            Topology topology, Dictionary<(string, string), Polynomial<TVar>> preInputVariables = null,
            Dictionary<(string, string), double> inputEqualityConstraints = null, bool noAdditionalConstraints = false,
            InnerRewriteMethodChoice innerEncoding = InnerRewriteMethodChoice.KKT,
            PathType pathType = PathType.KSP, Dictionary<(string, string), string[][]> selectedPaths = null,
            Dictionary<(int, string, string), double> historicInputConstraints = null,
            int numProcesses = -1)
        {
            throw new System.Exception("making sure that TE is defined...");
        }
        /// <summary>
        /// Encode the problem.
        /// </summary>
        /// <returns>The constraints and maximization objective.</returns>
        public OptimizationEncoding<TVar, TSolution> Encoding(Bins bins,
            Dictionary<int, List<TVar>> preInputVariables = null,
            Dictionary<int, List<double>> inputEqualityConstraints = null,
            Dictionary<int, int> inputPlacementEqualityConstraints = null,
            bool verbose = false)
        {
            throw new System.Exception("VBP Not Implemented....");
        }
        /// <summary>
        ///  Encode the PIFO problem.
        /// </summary>
        public OptimizationEncoding<TVar, TSolution> Encoding(
            Dictionary<int, TVar> preRankVariables = null,
            Dictionary<int, int> rankEqualityConstraints = null,
            bool verbose = false)
        {
            throw new System.Exception("PIFO Not Implemented....");
        }

        /// <summary>
        /// Get the optimization solution from the solver.
        /// </summary>
        /// <param name="solution">The solution.</param>
        public OptimizationSolution GetSolution(TSolution solution);

        /// <summary>
        /// Get the optimization solution from the solver.
        /// </summary>
        /// <param name="solution">The solution.</param>
        /// <param name="solutionNumber">which solution to return if multiple exist.</param>
        public OptimizationSolution GetSolution(TSolution solution, int solutionNumber)
        {
            throw new System.Exception("Not implemented for multiple solutions");
        }
    }
}
