using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using NLog;
    using ZenLib;
    /// <summary>
    /// Encodes demand pinning solution.
    /// </summary>
    public class DirectDemandPinningEncoder<TVar, TSolution> : IEncoder<TVar, TSolution>
    {
        private static readonly Logger Logger = LogManager.GetCurrentClassLogger();
        private double _threshold_tolerance = Math.Pow(10, -6);
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
        /// The threshold for the demand pinning problem.
        /// </summary>
        public double Threshold { get; set; }

        /// <summary>
        /// The enumeration of paths between all pairs of nodes.
        /// </summary>
        public Dictionary<(string, string), string[][]> Paths { get; set; }

        /// <summary>
        /// Absolute shortest paths.
        /// </summary>
        public Dictionary<(string, string), string[][]> absShortestPaths { get; set; }

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

        // /// <summary>
        // /// max for pinned flow.
        // /// </summary>
        // public Dictionary<(string, string), TVar> maxPinned { get; set; }

        private double _bigM = Math.Pow(10, 6);

        /// <summary>
        /// The flow variables for a given path in the network (f_k^p).
        /// </summary>
        public Dictionary<string[], TVar> FlowPathVariables { get; set; }

        /// <summary>
        /// The total demand met variable.
        /// </summary>
        public TVar TotalDemandMetVariable { get; set; }

        // /// <summary>
        // /// Those flows that are pinned.
        // /// </summary>
        // public Dictionary<(string, string), TVar> pinnedFlowVariables { get; set; }

        /// <summary>
        /// Sum non shortest path flows.
        /// </summary>
        public Dictionary<(string, string), Polynomial<TVar>> sumPaths { get; set; }

        /// <summary>
        /// The set of variables used in the encoding.
        /// </summary>
        private ISet<TVar> variables;

        private Dictionary<(string, string), double> link_to_cap_mapping;
        private double totalDemandPinned;

        /// <summary>
        /// Create a new instance of the <see cref="DirectDemandPinningEncoder{TVar, TSolution}"/> class.
        /// </summary>
        /// <param name="solver">The solver.</param>
        /// <param name="k">The max number of paths between nodes.</param>
        /// <param name="threshold"> The threshold to use for demand pinning.</param>
        public DirectDemandPinningEncoder(ISolver<TVar, TSolution> solver, int k, double threshold = 0)
        {
            this.Solver = solver;
            this.K = k;
            this.Threshold = threshold;
        }

        private void InitializeVariables(Dictionary<(string, string), double> demandConstraints, int numProcesses)
        {
            this.variables = new HashSet<TVar>();
            this.Paths = new Dictionary<(string, string), string[][]>();
            // establish the demand variables.
            this.DemandConstraints = new Dictionary<(string, string), double>(demandConstraints);

            // establish the total demand met variable.
            this.TotalDemandMetVariable = this.Solver.CreateVariable("total_demand_met");
            this.variables.Add(this.TotalDemandMetVariable);

            this.FlowVariables = new Dictionary<(string, string), TVar>();
            this.FlowPathVariables = new Dictionary<string[], TVar>(new PathComparer());
            this.sumPaths = new Dictionary<(string, string), Polynomial<TVar>>();

            this.link_to_cap_mapping = new Dictionary<(string, string), double>();
            foreach (var pair in this.Topology.GetAllEdges())
            {
                this.link_to_cap_mapping[(pair.Source, pair.Target)] = pair.Capacity;
            }
            this.totalDemandPinned = 0.0;
            foreach (var (pair, demand) in this.DemandConstraints)
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                if (demand <= Threshold + this._threshold_tolerance)
                {
                    var shortestPaths = this.Topology.ShortestKPaths(1, pair.Item1, pair.Item2);
                    if (shortestPaths.Count() <= 0)
                    {
                        continue;
                    }
                    for (int i = 0; i < shortestPaths[0].Count() - 1; i++)
                    {
                        var edge = (shortestPaths[0][i], shortestPaths[0][i + 1]);
                        this.link_to_cap_mapping[edge] -= demand;
                        if (this.link_to_cap_mapping[edge] < -1 * this._threshold_tolerance)
                        {
                            Logger.Debug(edge.Item1 + " " + edge.Item2 + " " + this.link_to_cap_mapping[edge]);
                            throw new DemandPinningLinkNegativeException("negative link capacity", edge, this.Threshold);
                        }
                        else
                        {
                            this.link_to_cap_mapping[edge] = Math.Max(0, this.link_to_cap_mapping[edge]);
                        }
                    }
                    this.totalDemandPinned += demand;
                    this.DemandConstraints[pair] = 0;
                }
            }
            Logger.Debug("Total Demand pinned = " + this.totalDemandPinned);
            this.Paths = this.Topology.MultiProcessAllPairsKShortestPath(this.K, numProcesses: numProcesses);
            foreach (var pair in this.Topology.GetNodePairs())
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                // establish the flow variable.
                this.FlowVariables[pair] = this.Solver.CreateVariable("flow_" + pair.Item1 + "_" + pair.Item2);
                this.variables.Add(this.FlowVariables[pair]);
                this.sumPaths[pair] = new Polynomial<TVar>(new Term<TVar>(0));

                foreach (var simplePath in this.Paths[pair])
                {
                    // establish the flow path variables.
                    this.FlowPathVariables[simplePath] = this.Solver.CreateVariable("flowpath_" + string.Join("_", simplePath));
                    this.variables.Add(this.FlowPathVariables[simplePath]);
                    this.sumPaths[pair].Add(new Term<TVar>(1, this.FlowPathVariables[simplePath]));
                }
            }
        }

        private bool IsDemandValid((string, string) pair)
        {
            if (this.DemandConstraints.ContainsKey(pair))
            {
                if (this.DemandConstraints[pair] < 0)
                {
                    throw new System.Exception("demands should be non-negative.");
                }
                else if (this.DemandConstraints[pair] == 0)
                {
                    return false;
                }
                return true;
            }
            throw new System.Exception("demand dict should contain all the pairs.");
        }
        /// <summary>
        /// Encode the problem.
        /// </summary>
        /// <returns>The constraints and maximization objective.</returns>
        public OptimizationEncoding<TVar, TSolution> Encoding(Topology topology, Dictionary<(string, string), Polynomial<TVar>> preDemandVariables = null,
            Dictionary<(string, string), double> demandEqualityConstraints = null, bool noAdditionalConstraints = false,
            InnerRewriteMethodChoice innerEncoding = InnerRewriteMethodChoice.KKT,
            PathType pathType = PathType.KSP, Dictionary<(string, string), string[][]> selectedPaths = null,
            int numProcesses = -1)
        {
            if (pathType != PathType.KSP) {
                throw new Exception("Only KSP works for now.");
            }

            this.Topology = topology;
            InitializeVariables(demandEqualityConstraints, numProcesses);
            // Compute the maximum demand M.
            // Since we don't know the demands we have to be very conservative.
            // var maxDemand = this.Topology.TotalCapacity() * 10;

            // Ensure that sum_k f_k = total_demand.
            // This includes both the ones that are pinned and
            // those that are not.
            var polynomial = new Polynomial<TVar>();
            foreach (var pair in this.Topology.GetNodePairs())
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                polynomial.Add(new Term<TVar>(1, this.FlowVariables[pair]));
            }

            // setting objective
            polynomial.Add(new Term<TVar>(-1, this.TotalDemandMetVariable));
            this.Solver.AddEqZeroConstraint(polynomial);

            // Ensure that f_k geq 0.
            // Ensure that f_k leq d_k.
            foreach (var (pair, variable) in this.FlowVariables)
            {
                // this.kktEncoder.AddLeqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(-1, variable)));
                var poly = new Polynomial<TVar>(new Term<TVar>(-1 * this.DemandConstraints[pair]));
                poly.Add(new Term<TVar>(1, variable));
                this.Solver.AddLeqZeroConstraint(poly);
            }

            // Ensure that f_k^p geq 0.
            foreach (var (pair, paths) in this.Paths)
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                foreach (var path in paths)
                {
                    this.Solver.AddLeqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(-1, this.FlowPathVariables[path])));
                }
            }

            // Ensure that the flow f_k = sum_p f_k^p.
            foreach (var (pair, paths) in this.Paths)
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                var poly = new Polynomial<TVar>(new Term<TVar>(0));
                foreach (var path in paths)
                {
                    poly.Add(new Term<TVar>(1, this.FlowPathVariables[path]));
                }

                poly.Add(new Term<TVar>(-1, this.FlowVariables[pair]));
                this.Solver.AddEqZeroConstraint(poly);
            }

            // Ensure the capacity constraints hold.
            // The sum of flows over all paths through each edge are bounded by capacity.
            var sumPerEdge = new Dictionary<Edge, Polynomial<TVar>>();
            // foreach (var edge in this.Topology.GetAllEdges())
            // {
            //     sumPerEdge[edge] = new Polynomial<TVar>(new Term<TVar>(0));
            // }

            foreach (var (pair, paths) in this.Paths)
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                foreach (var path in paths)
                {
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
                total.Add(new Term<TVar>(-1 * this.link_to_cap_mapping[(edge.Source, edge.Target)]));
                this.Solver.AddLeqZeroConstraint(total);
            }

            var objectiveFunction = new Polynomial<TVar>(new Term<TVar>(1, this.TotalDemandMetVariable), new Term<TVar>(this.totalDemandPinned));

            // Generate the full constraints.
            this.Solver.SetObjective(objectiveFunction);

            // Optimization objective is the total demand met.
            // Return the encoding, including the feasibility constraints, objective, and KKT conditions.
            return new TEOptimizationEncoding<TVar, TSolution>
            {
                GlobalObjective = this.TotalDemandMetVariable,
                MaximizationObjective = objectiveFunction,
                DemandVariables = this.DemandVariables,
            };
        }
        /// <summary>
        /// placeholder for getsolution.
        /// </summary>
        /// <param name="solution"></param>
        /// <returns></returns>
        public OptimizationSolution GetSolution(TSolution solution)
        {
            var demands = new Dictionary<(string, string), double>();
            var flows = new Dictionary<(string, string), double>();
            var flowPaths = new Dictionary<string[], double>(new PathComparer());

            // foreach (var (pair, poly) in this.DemandVariables)
            // {
            //     demands[pair] = 0;
            //     foreach (var term in poly.Terms) {
            //         demands[pair] += this.Solver.GetVariable(solution, term.Variable.Value) * term.Coefficient;
            //     }
            // }

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
                MaxObjective = this.Solver.GetVariable(solution, this.TotalDemandMetVariable) + this.totalDemandPinned,
                Demands = demands,
                Flows = flows,
                FlowsPaths = flowPaths,
            };
        }
    }
}
