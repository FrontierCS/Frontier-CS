// <copyright file="PopEncoder.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    using System.Diagnostics;
    using System.Linq;
    using NLog;

    /// <summary>
    /// The Pop encoder for splitting a network capacity into pieces.
    /// This encoder assumes the inner problem is the average performance
    /// over multiple partitions.
    /// </summary>
    public class ExpectedPopEncoder<TVar, TSolution> : IEncoder<TVar, TSolution>
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
        /// The number of samples for average.
        /// </summary>
        public int NumSamples { get; set; }

        /// <summary>
        /// the number of partitions per sample.
        /// </summary>
        public int numPartitionsPerSample { get; set; }

        /// <summary>
        /// List of DemandPartition Samples.
        /// </summary>
        public IList<IDictionary<(string, string), int>> DemandParitionsList { get; set; }

        /// <summary>
        /// List of Pop Encoders.
        /// </summary>
        public PopEncoder<TVar, TSolution>[] PoPEncoders { get; set; }

        /// <summary>
        /// The demand variables for the network (d_k).
        /// </summary>
        public Dictionary<(string, string), Polynomial<TVar>> DemandVariables { get; set; }

        /// <summary>
        /// The demand constraints in terms of constant values.
        /// </summary>
        public Dictionary<(string, string), double> DemandConstraints { get; set; }

        /// <summary>
        /// Create a new instance of the <see cref="ExpectedPopEncoder{TVar, TSolution}"/> class.
        /// </summary>
        public ExpectedPopEncoder(ISolver<TVar, TSolution> solver, int k, int numSamples, int numPartitionsPerSample,
                IList<IDictionary<(string, string), int>> demandPartitionsList)
        {
            if (numSamples <= 0)
            {
                throw new ArgumentOutOfRangeException("number of samples should be positive but got " + numSamples);
            }
            if (numPartitionsPerSample <= 0)
            {
                throw new ArgumentOutOfRangeException("number of paritions per sample should be positive but got" + numPartitionsPerSample);
            }
            if (demandPartitionsList.Count != numSamples)
            {
                throw new Exception("number of samples does not match the available partitionings in demandPartitionsList");
            }
            this.Solver = solver;
            this.K = k;
            this.NumSamples = numSamples;
            this.numPartitionsPerSample = numPartitionsPerSample;
            this.DemandParitionsList = demandPartitionsList;
            this.PoPEncoders = new PopEncoder<TVar, TSolution>[this.NumSamples];

            for (int i = 0; i < this.NumSamples; i++)
            {
                this.PoPEncoders[i] = new PopEncoder<TVar, TSolution>(solver, k, this.numPartitionsPerSample, this.DemandParitionsList[i]);
            }
        }

        private void InitializeVariables(Dictionary<(string, string), Polynomial<TVar>> preDemandVariables,
                Dictionary<(string, string), double> demandEnforcements)
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
            demandEnforcements = demandEnforcements ?? new Dictionary<(string, string), double>();
            this.DemandConstraints = demandEnforcements;
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
            Dictionary<(int, string, string), double> historicDemandConstraints = null,
            int numProcesses = -1)
        {
            if (pathType != PathType.KSP) {
                throw new Exception("Only KSP works for now.");
            }
            Debug.Assert(historicDemandConstraints == null);
            this.Topology = topology;
            Logger.Info("initializing variables for pop encoder.");
            InitializeVariables(preDemandVariables, demandEqualityConstraints);

            // Enforcing demands to be zero
            // List<string> validSources = new List<string>() { "0", "1" };
            // foreach (var pair in this.Topology.GetNodePairs()) {
            //     if (!validSources.Contains(pair.Item1)) {
            //         this.Solver.AddEqZeroConstraint(this.DemandVariables[pair]);
            //     }
            // }
            // Encoding each of the PoP samples
            var encodings = new OptimizationEncoding<TVar, TSolution>[this.NumSamples];
            for (int i = 0; i < this.NumSamples; i++)
            {
                Logger.Info(string.Format("generating pop encoding for sample {0}.", i));
                encodings[i] = this.PoPEncoders[i].Encoding(this.Topology, this.DemandVariables,
                                                            demandEqualityConstraints, noAdditionalConstraints, innerEncoding,
                                                            numProcesses: numProcesses);
            }
            // computing the objective value
            var objectiveVariable = this.Solver.CreateVariable("average_objective_pop");
            var objective = new Polynomial<TVar>(new Term<TVar>(-1 * this.NumSamples, objectiveVariable));
            foreach (var encdoing in encodings)
            {
                objective.Add(new Term<TVar>(1, encdoing.GlobalObjective));
            }
            this.Solver.AddEqZeroConstraint(objective);
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
            var demands = new Dictionary<(string, string), double>();
            var flows = new Dictionary<(string, string), double>();
            var flowPaths = new Dictionary<string[], double>(new PathComparer());

            var solutions = this.PoPEncoders.Select(e => (TEMaxFlowOptimizationSolution)e.GetSolution(solution)).ToList();

            foreach (var (pair, poly) in this.DemandVariables)
            {
                demands[pair] = 0;
                foreach (var term in poly.GetTerms())
                {
                    demands[pair] += this.Solver.GetVariable(solution, term.Variable.Value) * term.Coefficient;
                }
            }

            var eachSampleTotalDemandMet = new List<double>();
            foreach (var instance in solutions)
            {
                eachSampleTotalDemandMet.Add(instance.MaxObjective);
            }

            return new TEMaxFlowOptimizationSolution
            {
                MaxObjective = solutions.Select(s => s.MaxObjective).Aggregate((a, b) => a + b) / this.NumSamples,
                Demands = demands,
                Flows = null,
                FlowsPaths = null,
                TotalDemmandMetSample = eachSampleTotalDemandMet,
            };
        }
    }
}