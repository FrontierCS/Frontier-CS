using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Gurobi;

namespace MetaOptimize
{
    /// <summary>
    /// Implements a sanitized version of SolverGurobi.
    /// </summary>
    public class GurobiBinary : GurobiSOS
    {
        private double _bigM = Math.Pow(10, 8);
        private double _tolerance = Math.Pow(10, -8);
        private double _scale = Math.Pow(10, -5);

        /// <summary>
        /// Scales a polynomial.
        /// </summary>
        /// <param name="poly"></param>
        public Polynomial<GRBVar> scale(Polynomial<GRBVar> poly)
        {
            foreach (var term in poly.GetTerms())
            {
                term.Coefficient *= this._scale;
            }
            return poly;
        }

        /// <summary>
        /// Constructor.
        /// </summary>
        public GurobiBinary(double timeout = double.PositiveInfinity, int verbose = 0, int numThreads = 0, double timeToTerminateNoImprovement = -1,
                bool recordProgress = false, string logPath = null) : base(timeout, verbose, numThreads, timeToTerminateNoImprovement, recordProgress, logPath)
        {
        }

        /// <summary>
        /// Wrapper that convers the new types to guroubi types and then
        /// calls the proper function.
        /// </summary>
        /// <param name="polynomial1"></param>
        /// <param name="polynomial2"></param>
        public override void AddOrEqZeroConstraint(Polynomial<GRBVar> polynomial1, Polynomial<GRBVar> polynomial2)
        {
            GRBLinExpr poly1 = this.fromPolyToLinExpr(this.scale(polynomial1));
            GRBLinExpr poly2 = this.fromPolyToLinExpr(this.scale(polynomial2));
            GRBLinExpr poly2Neg = this.fromPolyToLinExpr(polynomial2.Negate());

            var alpha = this._model.AddVar(0.0, 1.0, 0.0, GRB.BINARY, "binary_" + this._auxiliaryVars.Count);
            this._auxiliaryVars.Add($"binary_{this._auxiliaryVars.Count}", alpha);

            poly1.AddTerm(-1 * this._bigM * this._scale, alpha);

            poly2.AddTerm(this._bigM * this._scale, alpha);
            poly2.AddConstant(-1 * this._bigM * this._scale);

            poly2Neg.AddTerm(this._bigM * this._scale, alpha);
            poly2Neg.AddConstant(-1 * this._bigM * this._scale);

            this._model.AddConstr(poly1, GRB.LESS_EQUAL, 0.0, "ineq_index_" + this._constraintIneqCount++);
            this._model.AddConstr(poly2, GRB.LESS_EQUAL, 0.0, "ineq_index_" + this._constraintIneqCount++);
            this._model.AddConstr(poly2Neg, GRB.LESS_EQUAL, 0.0, "ineq_index_" + this._constraintIneqCount++);
        }
        /// <summary>
        /// Maximize the objective.
        /// </summary>
        /// <returns>A solution.</returns>
        public override GRBModel Maximize()
        {
            Console.WriteLine("in maximize call");
            GRBLinExpr objective = 0;
            foreach (var auxVar in this.auxPolyList)
            {
                objective += this.fromPolyToLinExpr(auxVar) * (1 / this._bigM);
            }
            this._model.SetObjective(objective + this._objective, GRB.MAXIMIZE);
            // this._model.Parameters.DualReductions = 0;
            // this._model.Parameters.MIPFocus = 3;
            // this._model.Parameters.Cuts = 3;
            // this._model.Parameters.Heuristics = 0.5;

            this._model.Set(GRB.DoubleParam.IntFeasTol, this._tolerance);

            // string exhaust_dir_name = @"c:\tmp\grbsos_exhaust\rand_" + (new Random()).Next(1000000) + @"\";
            // Directory.CreateDirectory(exhaust_dir_name);
            // this._model.Write($"{exhaust_dir_name}\\model_" + DateTime.Now.Millisecond + ".lp");
            this._model.Optimize();
            if (this._model.Status != GRB.Status.TIME_LIMIT & this._model.Status != GRB.Status.OPTIMAL & this._model.Status != GRB.Status.INTERRUPTED)
            {
                throw new Exception($"model not optimal {ModelStatusToString(this._model.Status)}");
            }

            return this._model;
        }
    }
}
