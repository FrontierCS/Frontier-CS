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
    using ZenLib;

    /// <summary>
    /// The POP encoder for splitting a network capacity into pieces.
    /// </summary>
    public class PopEncoder<TVar, TSolution> : IEncoder<TVar, TSolution>
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
        public int maxNumPaths { get; set; }

        /// <summary>
        /// The reduced capacity topology for the network.
        /// POP partitions the network into identical topologies where
        /// each topology has an equal fraction of the link capacities from
        /// the original topology. Because of that we only need to keep
        /// one instance instead of n.
        /// </summary>
        public Topology ReducedTopology { get; set; }

        /// <summary>
        /// The number of partitions to use.
        /// </summary>
        public int NumPartitions { get; set; }

        /// <summary>
        /// Partitioning of the demands.
        /// </summary>
        public IDictionary<(string, string), int> DemandPartitions { get; set; }

        /// <summary>
        /// how different total demands can be in each partition.
        /// </summary>
        public double PartitionSensitivity { get; set; }

        /// <summary>
        /// The individual encoders for each partition.
        /// </summary>
        public TEMaxFlowOptimalEncoder<TVar, TSolution>[] PartitionEncoders { get; set; }

        /// <summary>
        /// The demand variables for the network (d_k).
        /// </summary>
        public Dictionary<(string, string), Polynomial<TVar>> DemandVariables { get; set; }

        /// <summary>
        /// The demand constraints in terms of constant values.
        /// Speficically, POP also partitions the demand matrix, so that each partition
        /// routes a sub-set of the demands. This dictionary maps the demands for each partition
        /// so that we track which demands the partition is serving and it is also tracking how large these
        /// demands are.
        /// </summary>
        public Dictionary<int, Dictionary<(string, string), double>> perPartitionDemandConstraints { get; set; }

        /// <summary>
        /// Create a new instance of the <see cref="PopEncoder{TVar, TSolution}"/> class.
        /// </summary>
        /// <param name="solver">The solver to use.</param>
        /// <param name="maxNumPaths">The max number of paths between nodes.</param>
        /// <param name="numPartitions">The number of partitions.</param>
        /// <param name="demandPartitions">The demand partitions.</param>
        /// <param name="partitionSensitivity">how different total demands can be in each partition.</param>
        public PopEncoder(ISolver<TVar, TSolution> solver, int maxNumPaths, int numPartitions, IDictionary<(string, string), int> demandPartitions,
            double partitionSensitivity = -1)
        {
            if (numPartitions <= 0)
            {
                throw new ArgumentOutOfRangeException("Partitions must be greater than zero.");
            }
            if (numPartitions > 10)
            {
                throw new ArgumentOutOfRangeException("Right now we only support up to 10 partitions.");
            }

            Logger.Debug("========= parition sensitivity: " + partitionSensitivity);
            if (partitionSensitivity != -1 & (partitionSensitivity < 0 | partitionSensitivity > 1))
            {
                throw new Exception("production sensitivity should be between 0 and 1");
            }

            this.Solver = solver;
            this.maxNumPaths = maxNumPaths;
            this.NumPartitions = numPartitions;
            this.DemandPartitions = demandPartitions;
            this.PartitionSensitivity = partitionSensitivity;

            this.PartitionEncoders = new TEMaxFlowOptimalEncoder<TVar, TSolution>[this.NumPartitions];

            for (int i = 0; i < this.NumPartitions; i++)
            {
                this.PartitionEncoders[i] = new TEMaxFlowOptimalEncoder<TVar, TSolution>(solver, this.maxNumPaths);
            }
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
            demandEnforcements = demandEnforcements ?? new Dictionary<(string, string), double>();
            this.perPartitionDemandConstraints = new Dictionary<int, Dictionary<(string, string), double>>();
            foreach (int i in Enumerable.Range(0, NumPartitions))
            {
                this.perPartitionDemandConstraints[i] = new Dictionary<(string, string), double>();
                foreach (var demand in this.DemandPartitions)
                {
                    if (demand.Value != i)
                    {
                        this.perPartitionDemandConstraints[i][demand.Key] = 0;
                    }
                    else if (demandEnforcements.ContainsKey(demand.Key))
                    {
                        this.perPartitionDemandConstraints[i][demand.Key] = demandEnforcements[demand.Key];
                    }
                }
            }
        }

        /// <summary>
        /// Encodes the POP optimization problem.
        /// The POP heuristic is described in the following paper
        /// by Narayanan et al: https://dl.acm.org/doi/10.1145/3477132.3483588
        /// The pathType encodes how we find the shortest path sets to use for
        /// the multi-commodity flow problem.
        /// </summary>
        /// <returns>The constraints and maximization objective.</returns>
        public OptimizationEncoding<TVar, TSolution> Encoding(
            Topology topology, Dictionary<(string, string), Polynomial<TVar>> preDemandVariables = null,
            Dictionary<(string, string), double> demandEqualityConstraints = null, bool noAdditionalConstraints = false,
            InnerRewriteMethodChoice innerEncoding = InnerRewriteMethodChoice.KKT,
            PathType pathType = PathType.KSP, Dictionary<(string, string), string[][]> selectedPaths = null,
            Dictionary<(int, string, string), double> historicInputConstraints = null,
            int numProcesses = -1)
        {
            if (pathType != PathType.KSP)
            {
                throw new Exception("Only KSP works for now.");
            }
            Debug.Assert(historicInputConstraints == null);
            this.Topology = topology;
            this.ReducedTopology = topology.SplitCapacity(this.NumPartitions);
            InitializeVariables(preDemandVariables, demandEqualityConstraints);

            // Create a new instance of the optimization encoding class for each partition.
            var encodings = new OptimizationEncoding<TVar, TSolution>[NumPartitions];

            // get all the separate encodings.
            for (int i = 0; i < this.NumPartitions; i++)
            {
                Logger.Info(string.Format("generating pop encoding for partition {0}.", i));
                Dictionary<(string, string), Polynomial<TVar>> partitionPreDemandVariables = null;
                partitionPreDemandVariables = new Dictionary<(string, string), Polynomial<TVar>>();
                foreach (var (pair, partitionID) in this.DemandPartitions)
                {
                    // TODO: is the second condition necessary? for pop aren't all nodes guaranteed to be in all topologies?
                    if (partitionID == i & this.Topology.GetAllNodes().Contains(pair.Item1) & this.Topology.GetAllNodes().Contains(pair.Item2))
                    {
                        partitionPreDemandVariables[pair] = this.DemandVariables[pair];
                    }
                }
                encodings[i] = this.PartitionEncoders[i].Encoding(this.ReducedTopology, partitionPreDemandVariables, this.perPartitionDemandConstraints[i], noAdditionalConstraints: noAdditionalConstraints,
                                                                innerEncoding: innerEncoding, numProcesses: numProcesses);
            }

            // create new demand variables as the sum of the individual partitions.
            var demandVariables = new Dictionary<(string, string), Polynomial<TVar>>();
            var partitionToTotalDemand = new Dictionary<int, Polynomial<TVar>>();
            foreach (var pair in this.Topology.GetNodePairs())
            {
                int partitionID = this.DemandPartitions[pair];
                if (this.PartitionEncoders[partitionID].DemandVariables.ContainsKey(pair))
                {
                    demandVariables[pair] = this.PartitionEncoders[partitionID].DemandVariables[pair];
                }
                else
                {
                    demandVariables[pair] = new Polynomial<TVar>();
                }

                if (!partitionToTotalDemand.ContainsKey(partitionID))
                {
                    partitionToTotalDemand[partitionID] = new Polynomial<TVar>();
                }
                partitionToTotalDemand[partitionID].Add(demandVariables[pair]);
            }

            // enforce sensitivity
            // TODO: need a better comment that describes what this means.
            if (this.PartitionSensitivity != -1)
            {
                for (int i = 0; i < this.NumPartitions; i++)
                {
                    for (int j = 0; j < this.NumPartitions; j++)
                    {
                        if (i == j)
                        {
                            continue;
                        }
                        var poly = partitionToTotalDemand[i].Copy().Multiply(-1 * (1 + this.PartitionSensitivity));
                        poly.Add(partitionToTotalDemand[j]);
                        this.Solver.AddLeqZeroConstraint(poly);
                    }
                }
            }
            // compute the objective to optimize.
            var objectiveVariable = this.Solver.CreateVariable("objective_pop");
            if (noAdditionalConstraints)
            {
                var maxDemand = this.Topology.TotalCapacity() * -10;
                this.Solver.AddLeqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(1, objectiveVariable), new Term<TVar>(maxDemand)));
            }
            var objective = new Polynomial<TVar>(new Term<TVar>(-1, objectiveVariable));
            foreach (var encoding in encodings)
            {
                objective.Add(new Term<TVar>(1, encoding.GlobalObjective));
            }

            this.Solver.AddEqZeroConstraint(objective);

            return new TEOptimizationEncoding<TVar, TSolution>
            {
                GlobalObjective = objectiveVariable,
                MaximizationObjective = new Polynomial<TVar>(new Term<TVar>(1, objectiveVariable)),
                DemandVariables = demandVariables,
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

            var solutions = this.PartitionEncoders.Select(e => (TEMaxFlowOptimizationSolution)e.GetSolution(solution)).ToList();

            // foreach (var pair in this.Topology.GetNodePairs())
            // {
            //     // demands[pair] = solutions.Select(s => s.Demands[pair]).Aggregate((a, b) => a + b);
            //     // flows[pair] = solutions.Select(s => s.Flows[pair]).Aggregate((a, b) => a + b);
            //     int partitionID = this.DemandPartitions[pair];
            //     demands[pair] = solutions[partitionID].Demands[pair];
            //     flows[pair] = solutions[partitionID].Flows[pair];
            // }

            // for (int i = 0; i < this.NumPartitions; i++) {
            //     foreach (var path in solutions[i].FlowsPaths.Keys)
            //     {
            //         // flowPaths[path] = solutions.Select(s => s.FlowsPaths[path]).Aggregate((a, b) => a + b);
            //         flowPaths[path] = solutions[i].FlowsPaths[path];
            //     }
            // }

            foreach (var (pair, poly) in this.DemandVariables)
            {
                demands[pair] = 0;
                foreach (var term in poly.GetTerms())
                {
                    demands[pair] += this.Solver.GetVariable(solution, term.Variable.Value) * term.Coefficient;
                }
            }

            for (int i = 0; i < this.NumPartitions; i++)
            {
                foreach (var (pair, variable) in this.PartitionEncoders[i].FlowVariables)
                {
                    flows[pair] = this.Solver.GetVariable(solution, variable);
                }

                foreach (var (path, variable) in this.PartitionEncoders[i].FlowPathVariables)
                {
                    flowPaths[path] = this.Solver.GetVariable(solution, variable);
                }
            }

            return new TEMaxFlowOptimizationSolution
            {
                MaxObjective = solutions.Select(s => s.MaxObjective).Aggregate((a, b) => a + b),
                Demands = demands,
                Flows = flows,
                FlowsPaths = flowPaths,
            };
        }
    }
}
