// <copyright file="OptimalEncoder.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    using System.Diagnostics;
    using NLog;

    /// <summary>
    /// A class for the optimal encoding.
    /// </summary>
    public class TEMaxFlowOptimalEncoder<TVar, TSolution> : IEncoder<TVar, TSolution>
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
        public int MaxNumPaths { get; set; }

        /// <summary>
        /// The enumeration of paths between all pairs of nodes.
        /// </summary>
        public Dictionary<(string, string), string[][]> Paths { get; set; }

        /// <summary>
        /// The demand constraints in terms of constant values.
        /// </summary>
        public Dictionary<(string, string), double> DemandConstraints { get; set; }

        /// <summary>
        /// The demand variables for the network (d_k).
        /// </summary>
        public Dictionary<(string, string), Polynomial<TVar>> DemandVariables { get; set; }

        /// <summary>
        /// The flow variables for the network (f_k).
        /// </summary>
        public Dictionary<(string, string), TVar> FlowVariables { get; set; }

        /// <summary>
        /// The flow variables for a given path in the network (f_k^p).
        /// </summary>
        public Dictionary<string[], TVar> FlowPathVariables { get; set; }

        /// <summary>
        /// The total demand met variable.
        /// </summary>
        public TVar TotalDemandMetVariable { get; set; }

        /// <summary>
        /// The set of variables used in the encoding.
        /// </summary>
        protected ISet<TVar> variables;

        /// <summary>
        /// The kkt encoder used to construct the encoding.
        /// </summary>
        protected KKTRewriteGenerator<TVar, TSolution> innerProblemEncoder;

        /// <summary>
        /// Create a new instance of the <see cref="TEMaxFlowOptimalEncoder{TVar, TSolution}"/> class.
        /// </summary>
        /// <param name="solver">The solver.</param>
        /// <param name="maxNumPaths">The max number of paths between nodes.</param>
        public TEMaxFlowOptimalEncoder(ISolver<TVar, TSolution> solver, int maxNumPaths)
        {
            this.Solver = solver;
            this.MaxNumPaths = maxNumPaths;
        }

        /// <summary>
        /// checks if demand between a pair of nodes is valid.
        /// </summary>
        /// <param name="pair"></param>
        /// <param name="checkInSet"></param>
        /// <returns></returns>
        protected bool IsDemandValid((string, string) pair, bool checkInSet = true)
        {
            if (!this.DemandVariables.ContainsKey(pair) && checkInSet)
            {
                return false;
            }
            if (this.DemandConstraints.ContainsKey(pair))
            {
                if (this.DemandConstraints[pair] <= 0)
                {
                    return false;
                }
            }
            return true;
        }

        /// <summary>
        /// Initializes the variables for the optimal encoding.
        /// </summary>
        /// <param name="preDemandVariables">Pre-specified demand variables.</param>
        /// <param name="demandEqualityConstraints">pre-specified demands.</param>
        /// <param name="rewriteMethod">What encoding to use (KKT or Primal-dual).</param>
        /// <param name="pathType">what algorithm to use to compute the set of candidate paths.</param>
        /// <param name="selectedPaths">Pre-selected paths for each demand.</param>
        /// <param name="numProcesses">Number of processes to use.</param>
        /// <exception cref="Exception"></exception>
        protected void InitializeVariables(Dictionary<(string, string), Polynomial<TVar>> preDemandVariables,
                Dictionary<(string, string), double> demandEqualityConstraints, InnerRewriteMethodChoice rewriteMethod,
                PathType pathType, Dictionary<(string, string), string[][]> selectedPaths,
                int numProcesses)
        {
            this.variables = new HashSet<TVar>();
            // establish the demand variables.
            this.DemandConstraints = demandEqualityConstraints ?? new Dictionary<(string, string), double>();
            this.DemandVariables = new Dictionary<(string, string), Polynomial<TVar>>();
            var demandVariables = new HashSet<TVar>();

            if (preDemandVariables == null)
            {
                this.DemandVariables = new Dictionary<(string, string), Polynomial<TVar>>();
                foreach (var pair in this.Topology.GetNodePairs())
                {
                    if (pair.Item1.Contains("-CombineWith-") || pair.Item2.Contains("-CombineWith-"))
                    {
                        continue;
                    }
                    if (!IsDemandValid(pair, false))
                    {
                        continue;
                    }
                    var variable = this.Solver.CreateVariable("demand_" + pair.Item1 + "_" + pair.Item2);
                    this.DemandVariables[pair] = new Polynomial<TVar>(new Term<TVar>(1, variable));
                    this.variables.Add(variable);
                    demandVariables.Add(variable);
                }
            }
            else
            {
                foreach (var (pair, variable) in preDemandVariables)
                {
                    if (!IsDemandValid(pair, false))
                    {
                        continue;
                    }
                    this.DemandVariables[pair] = variable;
                    foreach (var term in variable.GetTerms())
                    {
                        this.variables.Add(term.Variable.Value);
                        demandVariables.Add(term.Variable.Value);
                    }
                }
            }

            // establish the total demand met variable.
            this.TotalDemandMetVariable = this.Solver.CreateVariable("total_demand_met");
            this.variables.Add(this.TotalDemandMetVariable);

            this.FlowVariables = new Dictionary<(string, string), TVar>();
            this.FlowPathVariables = new Dictionary<string[], TVar>(new PathComparer());

            // compute the paths
            if (selectedPaths == null)
            {
                this.Paths = this.Topology.ComputePaths(pathType, selectedPaths, this.MaxNumPaths, numProcesses, false);
            }
            else
            {
                this.Paths = selectedPaths;
            }

            foreach (var pair in this.DemandVariables.Keys)
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                // establish the flow variable.
                this.FlowVariables[pair] = this.Solver.CreateVariable("flow_" + pair.Item1 + "_" + pair.Item2);
                this.variables.Add(this.FlowVariables[pair]);
                if (!this.Paths.ContainsKey(pair))
                {
                    continue;
                }
                foreach (var simplePath in this.Paths[pair])
                {
                    // establish the flow path variables.
                    this.FlowPathVariables[simplePath] = this.Solver.CreateVariable("flowpath_" + string.Join("_", simplePath));
                    this.variables.Add(this.FlowPathVariables[simplePath]);
                }
            }

            switch (rewriteMethod)
            {
                case InnerRewriteMethodChoice.KKT:
                    this.innerProblemEncoder = new KKTRewriteGenerator<TVar, TSolution>(this.Solver, this.variables, demandVariables);
                    break;
                case InnerRewriteMethodChoice.PrimalDual:
                    this.innerProblemEncoder = new PrimalDualRewriteGenerator<TVar, TSolution>(this.Solver,
                                                                                               this.variables,
                                                                                               demandVariables,
                                                                                               numProcesses);
                    break;
                default:
                    throw new Exception("invalid method for encoding the inner problem");
            }
        }

        /// <summary>
        /// Ensure sum_k f_k = total demand.
        /// </summary>
        /// <param name="topology"></param>
        public void EncodeTotalDemandConstraint(Topology topology)
        {
            Logger.Info("ensuring sum_k f_k = total demand");
            var totalFlowEquality = new Polynomial<TVar>();
            if (this.DemandVariables.Count != this.FlowVariables.Count)
            {
                throw new Exception("there is a bug in the code where the number of flow variables does not match the number of demands");
            }

            foreach (var (pair, demand) in this.DemandVariables)
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                totalFlowEquality.Add(new Term<TVar>(1, this.FlowVariables[pair]));
            }

            totalFlowEquality.Add(new Term<TVar>(-1, this.TotalDemandMetVariable));

            // TODO: we seem to re-use the kkt encoder when we don't want to do any rewrite (there is a condition in the KKT rewrite block that checks if
            // we want to do a rewrite or not i think). We should probably seperate that into its own instance of the rewrite interface and initiate the inner problem
            // encoder depending on whether we have an aligned follower or not.
            // TODO: when we want to re-factor this we should first write a test case, then create a deprecated instance of this file and check they produce the same answer.
            this.innerProblemEncoder.AddEqZeroConstraint(totalFlowEquality);
        }
        /// <summary>
        /// If there are demands that are pre-set this function
        /// ensures we have constraints that capture that.
        /// </summary>
        public void MeetPreSetDemands()
        {
            Logger.Info("ensuring demand constraints are respected");
            // These constraints ensure that if the demand value is prespecified that the optimization respects those allocations.
            foreach (var (pair, constant) in this.DemandConstraints)
            {
                if (constant <= 0)
                {
                    continue;
                }
                var demandConstraint = this.DemandVariables[pair].Copy();
                demandConstraint.Add(new Term<TVar>(-1 * constant));
                this.Solver.AddEqZeroConstraint(demandConstraint);
            }
        }

        /// <summary>
        /// Ensure that f_k geq 0.
        /// Ensure that f_k leq d_k.
        /// Ensure that f_k^p geq 0.
        /// </summary>
        public virtual void BoundFlowVariables()
        {
            Logger.Info("ensuring flows are within a correct range.");
            foreach (var (pair, variable) in this.FlowVariables)
            {
                var flowSizeConstraints = this.DemandVariables[pair].Negate();
                flowSizeConstraints.Add(new Term<TVar>(1, variable));
                this.innerProblemEncoder.AddLeqZeroConstraint(flowSizeConstraints);
            }
            Logger.Info("ensuring sum_k f_k^p geq 0");
            foreach (var (pair, paths) in this.Paths)
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                foreach (var path in paths)
                {
                    this.innerProblemEncoder.AddLeqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(-1, this.FlowPathVariables[path])));
                }
            }
        }

        /// <summary>
        /// Ensure that nodes that are not connected have no flow or demand.
        /// This is needed for not fully connected topologies.
        /// </summary>
        public virtual void EnsureNoFlowOnDisconnected()
        {
            Logger.Info("ensuring disconnected nodes do not have any flow");
            foreach (var (pair, paths) in this.Paths)
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                if (paths.Length == 0)
                {
                    this.innerProblemEncoder.AddEqZeroConstraint(this.DemandVariables[pair].Copy());
                    this.innerProblemEncoder.AddEqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(1, this.FlowVariables[pair])));
                }
            }
        }

        /// <summary>
        /// Ensure that the flow f_k = sum_p f_k^p.
        /// </summary>
        public virtual void ComputeTotalFlowPerDemand()
        {
            Logger.Info("ensuring f_k = sum_p f_k^p");
            foreach (var (pair, paths) in this.Paths)
            {
                if (!this.DemandVariables.ContainsKey(pair) && this.FlowVariables.ContainsKey(pair))
                {
                    throw new Exception("There is no demand variable for this pair but there is a flow variable.");
                }
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                var computeFlow = new Polynomial<TVar>(new Term<TVar>(0));
                foreach (var path in paths)
                {
                    computeFlow.Add(new Term<TVar>(1, this.FlowPathVariables[path]));
                }

                computeFlow.Add(new Term<TVar>(-1, this.FlowVariables[pair]));
                this.innerProblemEncoder.AddEqZeroConstraint(computeFlow);
            }
        }
        /// <summary>
        /// Adds capacity constraints.
        /// </summary>
        public void AddCapacityConstraints()
        {
            var sumPerEdge = new Dictionary<Edge, Polynomial<TVar>>();

            Logger.Info("ensuring capacity constraints");
            foreach (var (pair, paths) in this.Paths)
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                foreach (var path in paths)
                {
                    if (!this.DemandVariables.ContainsKey(pair) && this.FlowPathVariables.ContainsKey(path))
                    {
                        throw new Exception("There is no demand variable for this pair but there is a flow path variable.");
                    }
                    if (!this.DemandVariables.ContainsKey(pair))
                    {
                        continue;
                    }
                    for (int i = 0; i < path.Length - 1; i++)
                    {
                        var source = path[i];
                        var target = path[i + 1];
                        var edge = this.Topology.GetEdge(source, target);
                        var term = new Term<TVar>(1, this.FlowPathVariables[path]);
                        if (!sumPerEdge.ContainsKey(edge))
                        {
                            sumPerEdge[edge] = new Polynomial<TVar>(new Term<TVar>(0));
                        }
                        sumPerEdge[edge].Add(term);
                    }
                }
            }

            foreach (var (edge, total) in sumPerEdge)
            {
                total.Add(new Term<TVar>(-1 * edge.Capacity));
                this.innerProblemEncoder.AddLeqZeroConstraint(total);
            }
        }
        /// <summary>
        /// The encoder for the optimal TE problem.
        /// This solves the full form of the multi-commodity flow problem.
        /// </summary>
        /// <returns>The constraints and maximization objective.</returns>
        public OptimizationEncoding<TVar, TSolution> Encoding(Topology topology, Dictionary<(string, string), Polynomial<TVar>> preInputVariables = null,
            Dictionary<(string, string), double> inputEqualityConstraints = null, bool noAdditionalConstraints = false,
            InnerRewriteMethodChoice innerEncoding = InnerRewriteMethodChoice.KKT,
            PathType pathType = PathType.KSP, Dictionary<(string, string), string[][]> selectedPaths = null,
            Dictionary<(int, string, string), double> historicInputConstraints = null,
            int numProcesses = -1)
        {
            // Initialize Variables for the encoding
            Logger.Info("initializing variables");
            this.Topology = topology;
            InitializeVariables(preInputVariables, inputEqualityConstraints,
                innerEncoding, pathType, selectedPaths, numProcesses);
            // Compute the maximum demand M.
            // Since we don't know the demands we have to be very conservative.
            // var maxDemand = this.Topology.TotalCapacity() * 10;
            // var maxDemand = this.Topology.MaxCapacity() * this.K * 2;

            // Ensure that sum_k f_k = total_demand.
            EncodeTotalDemandConstraint(topology);

            // Ensure that the demand constraints are respected
            MeetPreSetDemands();

            // Ensure 0<= f_k <= d_k.
            BoundFlowVariables();

            // If we don't have a path between two nodes we should not have flow  between them.
            EnsureNoFlowOnDisconnected();

            // computes f_k = sum_p f_k^p.
            ComputeTotalFlowPerDemand();

            // Ensure the capacity constraints hold.
            // The sum of flows over all paths through each edge are bounded by capacity.
            AddCapacityConstraints();

            Logger.Info("generating full constraints");
            // Generate the full constraints.
            var objective = new Polynomial<TVar>(new Term<TVar>(1, this.TotalDemandMetVariable));
            Logger.Info("calling inner encoder");
            this.innerProblemEncoder.AddMaximizationConstraints(objective, noAdditionalConstraints);

            // Optimization objective is the total demand met.
            // Return the encoding, including the feasibility constraints, objective, and KKT conditions.
            return new TEOptimizationEncoding<TVar, TSolution>
            {
                GlobalObjective = this.TotalDemandMetVariable,
                MaximizationObjective = objective,
                DemandVariables = this.DemandVariables,
            };
        }

        /// <summary>
        /// Get the optimization solution from the solver solution.
        /// </summary>
        /// <param name="solution">The solution.</param>
        public virtual OptimizationSolution GetSolution(TSolution solution)
        {
            var demands = new Dictionary<(string, string), double>();
            var flows = new Dictionary<(string, string), double>();
            var flowPaths = new Dictionary<string[], double>(new PathComparer());

            foreach (var (pair, poly) in this.DemandVariables)
            {
                demands[pair] = 0;
                foreach (var term in poly.GetTerms())
                {
                    demands[pair] += this.Solver.GetVariable(solution, term.Variable.Value) * term.Coefficient;
                }
            }

            foreach (var (pair, variable) in this.FlowVariables)
            {
                flows[pair] = this.Solver.GetVariable(solution, variable);
            }

            foreach (var (path, variable) in this.FlowPathVariables)
            {
                flowPaths[path] = this.Solver.GetVariable(solution, variable);
            }

            return new TEMaxFlowOptimizationSolution
            {
                MaxObjective = this.Solver.GetVariable(solution, this.TotalDemandMetVariable),
                Demands = demands,
                Flows = flows,
                FlowsPaths = flowPaths,
            };
        }
    }
}
