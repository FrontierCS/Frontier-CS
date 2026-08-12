using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using NLog;

namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using ZenLib;
    /// <summary>
    /// Encodes demand pinning solution.
    /// </summary>
    public class ModifiedDemandPinningQuantizedEncoder<TVar, TSolution> : DemandPinningQuantizedEncoder<TVar, TSolution>
    {
        private static readonly Logger Logger = LogManager.GetCurrentClassLogger();
        /// <summary>
        /// Auxilary variable used to encode DP.
        /// </summary>
        private Dictionary<(string, string), Polynomial<TVar>> SPLowerBound { get; set; }
        private Dictionary<(string, string), Polynomial<TVar>> NSPUpperBound { get; set; }

        /// <summary>
        /// maximum shortest path length to pin.
        /// </summary>
        private int MaxShortestPathLen;

        /// <summary>
        /// Create a new instance of the <see cref="DemandPinningEncoder{TVar, TSolution}"/> class.
        /// </summary>
        /// <param name="solver">The solver.</param>
        /// <param name="k">The max number of paths between nodes.</param>
        /// <param name="MaxShortestPathLen">The maximum shortest path length to pin.</param>
        /// <param name="threshold"> The threshold to use for demand pinning.</param>
        /// <param name="scaleFactor"> The scale factor to show the input is downscaled.</param>
        public ModifiedDemandPinningQuantizedEncoder(ISolver<TVar, TSolution> solver, int k, int MaxShortestPathLen, double threshold = 0,
                double scaleFactor = 1.0) : base(solver, k, threshold, scaleFactor)
        {
            if (MaxShortestPathLen < 1)
            {
                throw new Exception("The max shortest path len should be >= 1 but received " + MaxShortestPathLen);
            }
            this.MaxShortestPathLen = MaxShortestPathLen;
        }

        /// <summary>
        /// Create auxiliary variables to model max() in DP formulation.
        /// </summary>
        protected override void CreateAuxVariable()
        {
            this.SPLowerBound = new Dictionary<(string, string), Polynomial<TVar>>();
            this.NSPUpperBound = new Dictionary<(string, string), Polynomial<TVar>>();
            foreach (var pair in this.Topology.GetNodePairs())
            {
                if (!IsDemandValid(pair))
                {
                    continue;
                }
                this.SPLowerBound[pair] = this.DemandVariables[pair].GetTermsWithCoeffLeq(this.Threshold);
                this.NSPUpperBound[pair] = this.DemandVariables[pair].GetTermsWithCoeffGreater(this.Threshold);
            }
        }

        /// <summary>
        /// verify output.
        /// </summary>
        protected override void VerifyOutput(TSolution solution, Dictionary<(string, string), double> demands, Dictionary<(string, string), double> flows)
        {
            foreach (var (pair, demand) in demands)
            {
                if (!flows.ContainsKey(pair))
                {
                    continue;
                }
                var shortestPaths = this.Topology.ShortestKPaths(1, pair.Item1, pair.Item2);
                if (shortestPaths[0].Count() <= this.MaxShortestPathLen)
                {
                    if (demand <= this.Threshold && Math.Abs(flows[pair] - demand) > 0.001)
                    {
                        Logger.Debug($"{pair.Item1},{pair.Item2},{demand},{flows[pair]}");
                        throw new Exception("does not match");
                    }
                }
                bool found = false;
                if (demand <= 0.001)
                {
                    found = true;
                }
                else
                {
                    foreach (var demandlvl in this.DemandVariables[pair].GetTerms())
                    {
                        if (Math.Abs(demand - demandlvl.Coefficient) <= 0.001)
                        {
                            found = true;
                        }
                    }
                }
                if (!found)
                {
                    Logger.Debug($"{pair.Item1},{pair.Item2},{demand},{flows[pair]}");
                    throw new Exception("does not match");
                }
            }
        }

        /// <summary>
        /// add Demand Pinning Constraints.
        /// </summary>
        protected override void GenerateDPConstraints(Polynomial<TVar> objectiveFunction)
        {
            Logger.Info("Generating Modified Quantized DP constraints.");
            // generating the max constraints that achieve pinning.
            foreach (var (pair, polyTerm) in sumNonShortestDict)
            {
                var shortestPaths = this.Topology.ShortestKPaths(1, pair.Item1, pair.Item2);
                if (shortestPaths[0].Count() <= this.MaxShortestPathLen)
                {
                    // shortest path flows \geq quantized demand with coefficient less than equal threshold
                    var shortestPathUB = this.SPLowerBound[pair].Copy();
                    shortestPathUB.Add(new Term<TVar>(-1, shortestFlowVariables[pair]));
                    this.innerProblemEncoder.AddLeqZeroConstraint(shortestPathUB);
                }
                else
                {
                    // for scalability reasons, zero out the variables <= threshold
                    var poly = this.DemandVariables[pair].GetTermsWithCoeffLeq(this.Threshold);
                    this.Solver.AddEqZeroConstraint(poly);
                }
            }
        }
    }
}
