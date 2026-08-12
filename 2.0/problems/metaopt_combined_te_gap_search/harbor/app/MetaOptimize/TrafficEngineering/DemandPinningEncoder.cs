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
    public class DemandPinningEncoder<TVar, TSolution> : IEncoder<TVar, TSolution>
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

        /// <summary>
        /// Auxilary variable used to encode maximum.
        /// </summary>
        private Dictionary<(string, string), TVar> MaxAuxVariables { get; set; }

        // /// <summary>
        // /// max for pinned flow.
        // /// </summary>
        // public Dictionary<(string, string), TVar> maxPinned { get; set; }

        private double _bigM = Math.Pow(10, 4);
        private double capacityTolerance = Math.Pow(10, -4);
        /// <summary>
        /// scale factor.
        /// TODO -- Engineering: right-now the scale factor is set to one.
        /// To use the scale factor you need to ensure that OPT also uses a similar factor.
        /// </summary>
        protected double _scale = Math.Pow(10, 0);

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
        public Dictionary<(string, string), Polynomial<TVar>> sumNonShortestDict { get; set; }

        /// <summary>
        /// Shortest path flow.
        /// </summary>
        public Dictionary<(string, string), TVar> shortestFlowVariables { get; set; }
        /// <summary>
        /// The set of variables used in the encoding.
        /// </summary>
        protected ISet<TVar> variables;

        /// <summary>
        /// The kkt encoder used to construct the encoding.
        /// </summary>
        protected KKTRewriteGenerator<TVar, TSolution> innerProblemEncoder;

        /// <summary>
        /// Create a new instance of the <see cref="DemandPinningEncoder{TVar, TSolution}"/> class.
        /// </summary>
        /// <param name="solver">The solver.</param>
        /// <param name="maxNumPaths">The max number of paths between nodes.</param>
        /// <param name="threshold"> The threshold to use for demand pinning.</param>
        /// <param name="scaleFactor"> The scale factor to show the input is downscaled.</param>
        public DemandPinningEncoder(ISolver<TVar, TSolution> solver, int maxNumPaths, double threshold = 0, double scaleFactor = 1.0)
        {
            this.Solver = solver;
            this.maxNumPaths = maxNumPaths;
            this.Threshold = threshold;
            this._bigM *= scaleFactor;
        }

        /// <summary>
        /// Create auxiliary variables to model max() in DP formulation.
        /// </summary>
        protected virtual void CreateAuxVariable()
        {
            this.MaxAuxVariables = new Dictionary<(string, string), TVar>();
            foreach (var pair in this.Topology.GetNodePairs())
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }

                this.MaxAuxVariables[pair] = this.Solver.CreateVariable("maxNonPinned_" + pair.Item1 + "_" + pair.Item2);
                this.variables.Add(this.MaxAuxVariables[pair]);
            }
        }

        /// <summary>
        /// Initializes the optimization variables for the Demand Pinning encoder.
        /// These variables are: the demand constraints which is a dictionary from (source, target) which are both strings to
        /// a double value. If the operator provides demand constraints as input (which is essentially pre-set values for the demands)
        /// then that would be the demand constraints, otherwise it initializes to an empty value set.
        /// The paths and the input demand variables are also set here (for example, pre-demand variables are sent into this function from the adversarial input generator).
        /// The demand variables --- the "input" to this problem.
        /// The function also creates variables for flow variables and other auxiliary variables.
        /// It also specifies the inner rewrite method choice.
        /// </summary>
        /// <param name="preDemandVariables"></param>
        /// <param name="demandConstraints"></param>
        /// <param name="innerEncoding"></param>
        /// <param name="numProcesses"></param>
        /// <exception cref="Exception"></exception>
        private void InitializeVariables(Dictionary<(string, string), Polynomial<TVar>> preDemandVariables, Dictionary<(string, string), double> demandConstraints,
                InnerRewriteMethodChoice innerEncoding = InnerRewriteMethodChoice.KKT, int numProcesses = -1)
        {
            this.variables = new HashSet<TVar>();
            this.Paths = new Dictionary<(string, string), string[][]>();
            // establish the demand variables.
            this.DemandConstraints = demandConstraints ?? new Dictionary<(string, string), double>();
            this.DemandVariables = preDemandVariables;
            var demandVariables = new HashSet<TVar>();

            if (this.DemandVariables == null)
            {
                this.DemandVariables = new Dictionary<(string, string), Polynomial<TVar>>();
                foreach (var pair in this.Topology.GetNodePairs())
                {
                    var variable = this.Solver.CreateVariable("demand_" + pair.Item1 + "_" + pair.Item2);
                    this.DemandVariables[pair] = new Polynomial<TVar>(new Term<TVar>(1, variable));
                    this.variables.Add(variable);
                    demandVariables.Add(variable);
                }
            }
            else
            {
                foreach (var (pair, variable) in this.DemandVariables)
                {
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

            // You need a better naming system for flow variables and flow path variables.
            this.FlowVariables = new Dictionary<(string, string), TVar>();
            this.FlowPathVariables = new Dictionary<string[], TVar>(new PathComparer());
            this.sumNonShortestDict = new Dictionary<(string, string), Polynomial<TVar>>();
            this.shortestFlowVariables = new Dictionary<(string, string), TVar>();

            this.Paths = this.Topology.MultiProcessAllPairsKShortestPath(this.maxNumPaths, numProcesses);
            foreach (var pair in this.Topology.GetNodePairs())
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                // establish the flow variable.
                this.FlowVariables[pair] = this.Solver.CreateVariable("flow_" + pair.Item1 + "_" + pair.Item2);
                this.variables.Add(this.FlowVariables[pair]);

                this.sumNonShortestDict[pair] = new Polynomial<TVar>(new Term<TVar>(0));
                var shortestPaths = this.Topology.ShortestKPaths(1, pair.Item1, pair.Item2);
                foreach (var simplePath in this.Paths[pair])
                {
                    // establish the flow path variables.
                    this.FlowPathVariables[simplePath] = this.Solver.CreateVariable("flowpath_" + string.Join("_", simplePath));
                    this.variables.Add(this.FlowPathVariables[simplePath]);
                    if (shortestPaths[0].SequenceEqual(simplePath))
                    {
                        this.shortestFlowVariables[pair] = this.FlowPathVariables[simplePath];
                    }
                    else
                    {
                        this.sumNonShortestDict[pair].Add(new Term<TVar>(1, this.FlowPathVariables[simplePath]));
                    }
                }
            }
            CreateAuxVariable();

            switch (innerEncoding)
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
        /// Check if demand is valid or not.
        /// </summary>
        protected bool IsDemandValid((string, string) pair)
        {
            if (this.DemandConstraints.ContainsKey(pair))
            {
                if (this.DemandConstraints[pair] <= 0)
                {
                    return false;
                }
            }
            if (this.Paths[pair].Length < 1)
            {
                return false;
            }
            return true;
        }
        /// <summary>
        /// Encode the problem.
        /// </summary>
        /// <returns>The constraints and maximization objective.</returns>
        public OptimizationEncoding<TVar, TSolution> Encoding(
            Topology topology, Dictionary<(string, string),
            Polynomial<TVar>> preDemandVariables = null,
            Dictionary<(string, string), double> demandConstraints = null, bool noAdditionalConstraints = false,
            InnerRewriteMethodChoice innerEncoding = InnerRewriteMethodChoice.KKT,
            PathType pathType = PathType.KSP, Dictionary<(string, string), string[][]> selectedPaths = null,
            Dictionary<(int, string, string), double> historicInputConstraints = null,
            int numProcesses = -1)
        {
            if (pathType != PathType.KSP || selectedPaths != null) {
                throw new Exception("Not implemented yet.");
            }

            Logger.Info("Demand Pinning with threshold = " + this.Threshold);
            this.Topology = topology;
            InitializeVariables(preDemandVariables, demandConstraints, innerEncoding, numProcesses);

            // Compute the maximum demand M.
            // Since we don't know the demands we have to be very conservative.
            // var maxDemand = this.Topology.TotalCapacity() * 10;

            // Ensure that sum_k f_k = total_demand.
            // This includes both the ones that are pinned and
            // those that are not.
            var totalDemandConstraintPoly = new Polynomial<TVar>();
            foreach (var pair in this.Topology.GetNodePairs())
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                totalDemandConstraintPoly.Add(new Term<TVar>(1, this.FlowVariables[pair]));
            }

            totalDemandConstraintPoly.Add(new Term<TVar>(-1 * this._scale, this.TotalDemandMetVariable));
            this.innerProblemEncoder.AddEqZeroConstraint(totalDemandConstraintPoly);

            // Ensure that the demand constraints are respected
            foreach (var (pair, constant) in this.DemandConstraints)
            {
                if (constant <= 0)
                {
                    continue;
                }
                var demandConstraint = this.DemandVariables[pair].Copy();
                demandConstraint.Add(new Term<TVar>(-1 * constant));
                this.innerProblemEncoder.AddEqZeroConstraint(demandConstraint);
            }

            // Ensure that f_k geq 0.
            // Ensure that f_k leq d_k.
            foreach (var (pair, variable) in this.FlowVariables)
            {
                // this.kktEncoder.AddLeqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(-1, variable)));
                var flowCapConstraint = this.DemandVariables[pair].Negate().Multiply(this._scale);
                flowCapConstraint.Add(new Term<TVar>(1, variable));
                this.innerProblemEncoder.AddLeqZeroConstraint(flowCapConstraint);
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
                    this.innerProblemEncoder.AddLeqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(-1, this.FlowPathVariables[path])));
                }
            }

            // Ensure that the flow f_k = sum_p f_k^p.
            foreach (var (pair, paths) in this.Paths)
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                var totalFlowPerDemandConstraint = new Polynomial<TVar>(new Term<TVar>(0));
                foreach (var path in paths)
                {
                    totalFlowPerDemandConstraint.Add(new Term<TVar>(1, this.FlowPathVariables[path]));
                }

                totalFlowPerDemandConstraint.Add(new Term<TVar>(-1, this.FlowVariables[pair]));
                this.innerProblemEncoder.AddEqZeroConstraint(totalFlowPerDemandConstraint);
            }

            // Ensure the capacity constraints hold.
            // The sum of flows over all paths through each edge are bounded by capacity.
            var sumPerEdge = new Dictionary<Edge, Polynomial<TVar>>();

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
                total.Add(new Term<TVar>(-1 * this._scale * edge.Capacity));
                this.innerProblemEncoder.AddLeqZeroConstraint(total);
            }

            var objectiveFunction = new Polynomial<TVar>(new Term<TVar>(this._scale, this.TotalDemandMetVariable));
            GenerateDPConstraints(objectiveFunction);

            // Generate the full constraints.
            this.innerProblemEncoder.AddMaximizationConstraints(objectiveFunction, noAdditionalConstraints);

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
        /// The demand pinning constraints, this is equivalent to the Appendix section A.3 in the MetaOpt paper.
        /// </summary>.
        protected virtual void GenerateDPConstraints(Polynomial<TVar> objectiveFunction)
        {
            // generating the max constraints that achieve pinning.
            Logger.Info("Generating DP constraints.");
            foreach (var (pair, sumNonShortestPoly) in sumNonShortestDict)
            {
                // MaxAuxVariables \geq 0
                this.innerProblemEncoder.AddLeqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(-1, MaxAuxVariables[pair])));
                // MaxAuxVariables \geq M(d_k - T_d)
                var maxNonPinnedLB = this.DemandVariables[pair].Multiply(this._scale * this._bigM);
                maxNonPinnedLB.Add(new Term<TVar>(-1 * this._scale * this._bigM * Threshold));
                maxNonPinnedLB.Add(new Term<TVar>(-1, MaxAuxVariables[pair]));
                this.innerProblemEncoder.AddLeqZeroConstraint(maxNonPinnedLB);

                // sum non shortest flows \leq MaxAuxVariables
                sumNonShortestPoly.Add(new Term<TVar>(-1, MaxAuxVariables[pair]));
                this.innerProblemEncoder.AddLeqZeroConstraint(sumNonShortestPoly);
                // Up to this point MaxAuxVariables = max(0, M(d_k - T_d), sum non shortest flows))

                // demand - shortest path flows \leq MaxAuxVariables
                var shortestPathUB = this.DemandVariables[pair].Multiply(this._scale);
                shortestPathUB.Add(new Term<TVar>(-1, shortestFlowVariables[pair]));
                shortestPathUB.Add(new Term<TVar>(-1, MaxAuxVariables[pair]));
                this.innerProblemEncoder.AddLeqZeroConstraint(shortestPathUB);
                // adding maxAuxVariable to the constants of the inner encoder
                // this.innerProblemEncoder.AddConstantVar(MaxAuxVariables[pair]);
            }

            double alpha = Math.Ceiling(this.Topology.TotalCapacity() * 1.1);
            Logger.Debug("$$$$$$ alpha value for demand pinning objective = " + alpha);
            foreach (var (pair, maxVar) in MaxAuxVariables)
            {
                objectiveFunction.Add(new Term<TVar>(-1 * alpha, maxVar));
                // this.Solver.AddGlobalTerm(this.DemandVariables[pair].Multiply(Math.Round(-1 / alpha, 3)));
            }
        }

        /// <summary>
        /// verify output.
        /// </summary>
        protected virtual void VerifyOutput(TSolution solution, Dictionary<(string, string), double> demands, Dictionary<(string, string), double> flows)
        {
            foreach (var (pair, demand) in demands)
            {
                if (!flows.ContainsKey(pair))
                {
                    continue;
                }
                if (demand <= this.Threshold && Math.Abs(flows[pair] - demand) > 0.001)
                {
                    Logger.Debug($"{pair.Item1},{pair.Item2},{demand},{flows[pair]}");
                    Logger.Debug($"max aux variable {this.Solver.GetVariable(solution, this.MaxAuxVariables[pair])}");
                    throw new Exception("does not match");
                }
            }
        }

        /// <summary>
        /// The function that parses the solution.
        /// </summary>
        /// <param name="solution"></param>
        /// <returns></returns>
        public OptimizationSolution GetSolution(TSolution solution)
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
                flows[pair] = this.Solver.GetVariable(solution, variable) / this._scale;
            }

            foreach (var (path, variable) in this.FlowPathVariables)
            {
                flowPaths[path] = this.Solver.GetVariable(solution, variable) / this._scale;
            }

            VerifyOutput(solution, demands, flows);

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
