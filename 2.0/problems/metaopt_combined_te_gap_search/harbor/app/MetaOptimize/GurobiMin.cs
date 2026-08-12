using System;
using System.Collections.Generic;
using System.Linq;
using Gurobi;

namespace MetaOptimize
{
    /// <summary>
    /// Uses the min of two positive
    /// functions instead of SoS variables.
    /// </summary>
    public class GurobiMin : GurobiSOS
    {
        /// <summary>
        /// Ensure at least one of these terms is zero.
        /// </summary>
        /// <param name="polynomial1"></param>
        /// <param name="polynomial2"></param>
        public override void AddOrEqZeroConstraint(Polynomial<GRBVar> polynomial1, Polynomial<GRBVar> polynomial2)
        {
            this.AddOrEqZeroConstraint(this.fromPolyToLinExpr(polynomial1), this.fromPolyToLinExpr(polynomial2.Negate()));
        }
        /// <summary>
        /// Over-rides the method in NoParams.
        /// </summary>
        /// <param name="expr1"></param>
        /// <param name="expr2"></param>
        public void AddOrEqZeroConstraint(GRBLinExpr expr1, GRBLinExpr expr2)
        {
            // Create auxilary variable for each polynomial
            var var_1 = this._model.AddVar(Double.NegativeInfinity, Double.PositiveInfinity, 0, GRB.CONTINUOUS, "aux_" + this._auxiliaryVars.Count);
            this._auxiliaryVars.Add($"aux_{this._auxiliaryVars.Count}", var_1);

            var var_2 = this._model.AddVar(Double.NegativeInfinity, Double.PositiveInfinity, 0, GRB.CONTINUOUS, "aux_" + this._auxiliaryVars.Count);
            this._auxiliaryVars.Add($"aux_{this._auxiliaryVars.Count}", var_2);

            this._model.AddConstr(expr1, GRB.EQUAL, var_1, "eq_index_" + this._constraintEqCount++);
            this._model.AddConstr(expr2, GRB.EQUAL, var_2, "eq_index_" + this._constraintEqCount++);

            // add min constraint
            var auxiliaries = new GRBVar[] { var_1, var_2 };
            var MinResult = this._model.AddVar(Double.NegativeInfinity, Double.PositiveInfinity, 0, GRB.CONTINUOUS, "MinResult_" + this._auxiliaryVars.Count);
            this._auxiliaryVars.Add($"MinResult_{this._auxiliaryVars.Count}", MinResult);
            this._model.AddGenConstrMin(MinResult, auxiliaries, Double.PositiveInfinity, $"auxC_{this._auxiliaryVars.Count}");
            this._model.AddConstr(MinResult, GRB.EQUAL, 0, "MinConstr_" + this._constraintEqCount++);
        }
    }
}
