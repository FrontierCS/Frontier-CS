// <copyright file="PopEncoder.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using Gurobi;
    using NLog;
    using ZenLib;

    /// <summary>
    /// The Pop encoder for splitting a network capacity into pieces.
    /// </summary>
    public class TECombineHeuristicsEncoder<TVar, TSolution> : IEncoder<TVar, TSolution>
    {
        private static readonly Logger Logger = LogManager.GetCurrentClassLogger();
        /// <summary>
        /// The solver being used.
        /// </summary>
        public ISolver<TVar, TSolution> Solver { get; set; }

        /// <summary>
        /// The topology for the network.
        /// </summary>
        public Topology Topology { get; set; }

        /// <summary>
        /// The maximum number of paths to use between any two nodes.
        /// </summary>
        public int K { get; set; }

        /// <summary>
        /// The demand variables for the network (d_k).
        /// </summary>
        public Dictionary<(string, string), Polynomial<TVar>> DemandVariables { get; set; }

        /// <summary>
        /// The demand constraints in terms of constant values.
        /// </summary>
        public Dictionary<(string, string), double> DemandConstraints { get; set; }

        /// <summary>
        /// The list of heuristic encoders to combine.
        /// </summary>
        public IList<IEncoder<TVar, TSolution>> HeuristicEncoderList { get; set; }

        /// <summary>
        /// The list of heuristic encodings to combine.
        /// </summary>
        public IDictionary<IEncoder<TVar, TSolution>, OptimizationEncoding<TVar, TSolution>> HeuristicEncodingDict { get; set; }

        /// <summary>
        /// binaries to see which heuristic is chosen.
        /// </summary>
        public Dictionary<OptimizationEncoding<TVar, TSolution>, TVar> WhichHeuristicBinary { get; set; }

        /// <summary>
        /// Create a new instance of the <see cref="TECombineHeuristicsEncoder{TVar, TSolution}"/> class.
        /// </summary>
        public TECombineHeuristicsEncoder(ISolver<TVar, TSolution> solver, IList<IEncoder<TVar, TSolution>> heuristicEncoderList, int k)
        {
            foreach (var heuristicEncoder in heuristicEncoderList)
            {
                if (solver != heuristicEncoder.Solver)
                {
                    throw new Exception("Solver mismatch between combiner and heuristic encoders.");
                }
            }
            this.HeuristicEncoderList = heuristicEncoderList;
            this.Solver = solver;
            this.K = k;
        }

        private void InitializeVariables(Dictionary<(string, string), Polynomial<TVar>> preDemandVariables, Dictionary<(string, string), double> demandEnforcements)
        {
            // establish the demand variables.
            this.DemandVariables = preDemandVariables;
            if (this.DemandVariables == null)
            {
                this.DemandVariables = new Dictionary<(string, string), Polynomial<TVar>>();
                foreach (var pair in this.Topology.GetNodePairs())
                {
                    this.DemandVariables[pair] = new Polynomial<TVar>(new Term<TVar>(1, this.Solver.CreateVariable("demand_" + pair.Item1 + "_" + pair.Item2)));
                }
            }
            this.DemandConstraints = demandEnforcements ?? new Dictionary<(string, string), double>();
        }

        /// <summary>
        /// Encode the problem.
        /// </summary>
        /// <returns>The constraints and maximization objective.</returns>
        public OptimizationEncoding<TVar, TSolution> Encoding(
            Topology topology, Dictionary<(string, string), Polynomial<TVar>> preDemandVariables = null,
            Dictionary<(string, string), double> demandEqualityConstraints = null, bool noAdditionalConstraints = false,
            InnerRewriteMethodChoice innerEncoding = InnerRewriteMethodChoice.KKT,
            PathType pathType = PathType.KSP, Dictionary<(string, string), string[][]> selectedPaths = null,
            int numProcesses = -1)
        {
            if (pathType != PathType.KSP) {
                throw new Exception("Only KSP works for now.");
            }
            this.Topology = topology;
            InitializeVariables(preDemandVariables, demandEqualityConstraints);
            this.HeuristicEncodingDict = new Dictionary<IEncoder<TVar, TSolution>, OptimizationEncoding<TVar, TSolution>>();

            // get all the separate encodings.
            Logger.Debug("generating encoding for heuristics.");
            foreach (var heruisticEncoder in this.HeuristicEncoderList)
            {
                var encoding = heruisticEncoder.Encoding(this.Topology, this.DemandVariables, demandEqualityConstraints,
                                                                noAdditionalConstraints: noAdditionalConstraints, innerEncoding: innerEncoding,
                                                                numProcesses: numProcesses);
                this.HeuristicEncodingDict[heruisticEncoder] = encoding;
            }

            // compute the objective to optimize.
            var objectiveVariable = this.Solver.CreateVariable("objective_combined");
            if (noAdditionalConstraints)
            {
                var maxDemand = this.Topology.TotalCapacity() * -10;
                this.Solver.AddLeqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(1, objectiveVariable), new Term<TVar>(maxDemand)));
            }

            // objective = maximum of objective of each hueristic
            // to model C = max(a_i), we add three sets of constraints.
            // C >= a_i for all i.
            // C <= a_i + (1 - b_i) * M for all i and binary variable b_i.
            // \sum (b_i) = 1.
            var objective = new Polynomial<TVar>(new Term<TVar>(-1, objectiveVariable));
            var sumBinaries = new Polynomial<TVar>();
            var maxObj = Topology.MaxCapacity() * this.K;
            this.WhichHeuristicBinary = new Dictionary<OptimizationEncoding<TVar, TSolution>, TVar>();
            foreach (var (encoder, encoding) in this.HeuristicEncodingDict)
            {
                var lb = objective.Copy();
                lb.Add(new Term<TVar>(1, encoding.GlobalObjective));
                this.Solver.AddLeqZeroConstraint(lb);

                var binaryMax = Solver.CreateVariable("binaryMax", type: GRB.BINARY);
                this.WhichHeuristicBinary[encoding] = binaryMax;
                var ub = objective.Negate();
                ub.Add(new Term<TVar>(-1, encoding.GlobalObjective));
                ub.Add(new Term<TVar>(-1 * maxObj));
                ub.Add(new Term<TVar>(maxObj, binaryMax));
                this.Solver.AddLeqZeroConstraint(ub);

                sumBinaries.Add(new Term<TVar>(-1, binaryMax));
            }
            sumBinaries.Add(new Term<TVar>(1));
            this.Solver.AddEqZeroConstraint(sumBinaries);

            return new TEOptimizationEncoding<TVar, TSolution>
            {
                GlobalObjective = objectiveVariable,
                MaximizationObjective = new Polynomial<TVar>(new Term<TVar>(1, objectiveVariable)),
                DemandVariables = this.DemandVariables,
            };
        }

        /// <summary>
        /// Get the optimization solution from the solver solution.
        /// </summary>
        /// <param name="solution">The solution.</param>
        public OptimizationSolution GetSolution(TSolution solution)
        {
            IEncoder<TVar, TSolution> chosenHeuristic = null;
            foreach (var (heuristicEncoder, heurisicEncoding) in this.HeuristicEncodingDict)
            {
                var chosen = this.Solver.GetVariable(solution, this.WhichHeuristicBinary[heurisicEncoding]);
                Logger.Debug(chosen);
                if (chosen == 1)
                {
                    chosenHeuristic = heuristicEncoder;
                }
            }

            return chosenHeuristic.GetSolution(solution);
        }
    }
}
