using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Reflection.Metadata.Ecma335;
using System.Text;
using System.Threading.Tasks;
using Gurobi;
using Microsoft.VisualBasic.FileIO;
using Microsoft.Z3;
using ZenLib;

namespace MetaOptimize
{
    /// <summary>
    /// Gurobi solver.
    /// Todo: may need to rethink the second argument to the class.
    /// Right now assuming we have a dictionary that maps var names to
    /// guroubi variables.
    /// </summary>
    public class SolverGurobi : ISolver<GRBVar, GRBModel>
    {
        private double _tolerance = Math.Pow(10, 8);

        private double _varBounds = Math.Pow(10, 6);
        /// <summary>
        /// scale factor for the variable.
        /// </summary>
        public double _scaleFactor = Math.Pow(10, 3);
        /// <summary>
        /// The solver variables.
        /// </summary>
        public ISet<GRBVar> _variables = new HashSet<GRBVar>();
        /// <summary>
        /// Stores variable names.
        /// </summary>
        public ISet<string> _varNames = new HashSet<string>();

        /// <summary>
        /// auxilary variables we are using
        /// to encode SOS constraints.
        /// </summary>
        private List<GRBVar> _auxilaryVars = new List<GRBVar>();

        private List<string> _auxiliaryVarNames = new List<string>();
        /// <summary>
        /// inequality constraints.
        /// </summary>
        public IList<GRBLinExpr> _constraintIneq = new List<GRBLinExpr>();
        /// <summary>
        /// equality constraints.
        /// </summary>
        public IList<GRBLinExpr> _constraintEq = new List<GRBLinExpr>();
        /// <summary>
        /// Keeps track of sos aux.
        /// </summary>
        private List<GRBVar[]> _SOSauxilaries = new List<GRBVar[]>();
        /// <summary>
        /// Used for the approx form.
        /// </summary>
        private List<GRBVar> _binaryVars = new List<GRBVar>();
        /// <summary>
        /// The gurobi model.
        /// </summary>
        public GRBModel _model = null;

        private GRBLinExpr _objective = 0;

        private bool _modelRun;

        /// <summary>
        /// constructor with scalefactor.
        /// </summary>
        /// <param name="varbound"></param>
        public SolverGurobi(double varbound)
        {
            this._varBounds = varbound;
            this._model = new GRBModel(GurobiEnvironment.Instance);
            this._model.Parameters.Presolve = 2;
        }

        /// <summary>
        /// Reset the solver by removing all the variables and constraints.
        /// </summary>
        public void CleanAll(double timeout = -1, bool disableStoreProgress = false) {
            this._model.Dispose();
            this._model = new GRBModel(GurobiEnvironment.Instance);
            this._model.Parameters.Presolve = 2;
        }

        /// <summary>
        /// Reset the solver by removing all the variables and constraints.
        /// </summary>
        public void CleanAll(bool focusBstBd, double timeout = -1) {
            throw new Exception("not implemented yet");
        }

        /// <summary>
        /// append as the next line of the store progress file.
        /// </summary>
        public void AppendToStoreProgressFile(double time_ms, double gap, bool reset = false) {
            throw new Exception("not implemented yet");
        }

        /// <summary>
        /// constructor.
        /// </summary>
        public SolverGurobi()
        {
            this._model = new GRBModel(GurobiEnvironment.Instance);
        }
        /// <summary>
        /// Get the timeout value.
        /// </summary>
        public double GetTimeout()
        {
            throw new Exception("This solver does not use a timeout yet");
        }
        /// <summary>
        /// set the timeout.
        /// </summary>
        /// <param name="timeout">value for timeout.</param>
        public void SetTimeout(double timeout) {
            throw new Exception("have not implemented yet");
        }

        /// <summary>
        /// set the FocusBstBd.
        /// </summary>
        public void SetFocusBstBd(bool focusBstBd) {
            throw new Exception("have not implemented yet");
        }

        /// <summary>
        /// get model.
        /// </summary>
        public GRBModel GetModel() {
            return this._model;
        }

        /// <summary>
        /// Create a new variable with a given name.
        /// </summary>
        /// <param name="name">The variable name.</param>
        /// <param name="type">The variable type.</param>
        /// <param name="lb">The lb on variable.</param>
        /// <param name="ub">The ub on variable.</param>
        /// <returns>The solver variable.</returns>
        public GRBVar CreateVariable(string name, char type = GRB.CONTINUOUS,
            double lb = double.NegativeInfinity, double ub = double.PositiveInfinity)
        {
            GRBVar variable;
            if (name == "")
            {
                throw new Exception("bug");
            }
            lb = Math.Max(-1 * this._varBounds, lb);
            ub = Math.Min(this._varBounds, ub);
            try
            {
                string new_name = name + "_" + this._variables.Count;
                variable = _model.AddVar(lb, ub, 0, type, new_name);
                this._variables.Add(variable);
                this._varNames.Add(new_name);
                return variable;
            }
            catch (GRBException ex)
            {
                System.Console.WriteLine(ex.Message);
            }
            return null;
        }

        /// <summary>
        /// Create a new continuous variable with a given name.
        /// </summary>
        public GRBVar CreateContinuousVariable(string name, double lb = double.NegativeInfinity, double ub = double.PositiveInfinity)
        {
            return this.CreateVariable(name, type: GRB.CONTINUOUS, lb: lb, ub: ub);
        }

        /// <summary>
        /// Create a new binary variable with a given name.
        /// </summary>
        public GRBVar CreateBinaryVariable(string name)
        {
            return this.CreateVariable(name, type: GRB.BINARY);
        }

        /// <summary>
        /// Create a new integer variable with a given name.
        /// </summary>
        public GRBVar CreateIntegerVariable(string name, double lb = double.NegativeInfinity, double ub = double.PositiveInfinity)
        {
            return this.CreateVariable(name, type: GRB.INTEGER, lb: lb, ub: ub);
        }

        /// <summary>
        /// Get the resulting value assigned to a variable.
        /// </summary>
        /// <param name="objective">The solver solution.</param>
        public void SetObjective(Polynomial<GRBVar> objective) {
            this._objective = convertPolynomialToLinExpr(objective);
        }

        /// <summary>
        /// Get the resulting value assigned to a variable.
        /// </summary>
        /// <param name="objective">The solver solution.</param>
        public void SetObjective(GRBVar objective) {
            this._objective = objective;
        }

        /// <summary>
        /// Get the resulting value assigned to a variable.
        /// </summary>
        /// <param name="objective">The solver solution.</param>
        public void SetObjective(GRBLinExpr objective) {
            this._objective = objective;
        }

        /// <summary>
        /// sets the scalefactor to use.
        /// </summary>
        /// <param name="scalefactor"></param>
        public void setScaleFactor(double scalefactor)
        {
            this._scaleFactor = scalefactor;
        }
        /// <summary>
        /// Converts polynomials to linear expressions.
        /// </summary>
        /// <param name="poly"></param>
        /// <returns></returns>
        public GRBLinExpr convertPolynomialToLinExpr(Polynomial<GRBVar> poly)
        {
            // original: - M < x < M; M = Double.MaxValue
            // original : a * x + b <=0
            // bounds on X : -M < x < M ==> -c < x < c
            // My prior change: a / c * x + b / c <= 0
            GRBLinExpr obj = 0;
            foreach (var term in poly.GetTerms())
            {
                if (term.Exponent == 1)
                {
                    obj.AddTerm(term.Coefficient / this._scaleFactor, (dynamic)term.Variable.Value);
                }
                else
                {
                    obj += (term.Coefficient / this._scaleFactor);
                }
            }
            return obj;
        }
        /// <summary>
        /// wrapper that does type conversions then calls the original function.
        /// </summary>
        /// <param name="polynomial"></param>
        public string AddLeqZeroConstraint(Polynomial<GRBVar> polynomial)
        {
            GRBLinExpr poly = this.convertPolynomialToLinExpr(polynomial);
            string name = this.AddLeqZeroConstraint(poly);
            return name;
        }
        /// <summary>
        /// Add a less than or equal to zero constraint.
        /// </summary>
        /// <param name="polynomial">The polynomial.</param>
        public string AddLeqZeroConstraint(GRBLinExpr polynomial)
        {
            string name = "ineq_index_" + this._constraintIneq.Count;
            this._model.AddConstr(polynomial, GRB.LESS_EQUAL,
                (Double)0, name);
            this._constraintIneq.Add(polynomial);
            return name;
        }

        /// <summary>
        /// Add a less than or equal to zero constraint (Quadratic).
        /// Following constraints; A * B + C \leq 0.
        /// </summary>
        public string AddLeqZeroConstraint(IList<Polynomial<GRBVar>> coeffPolyList, IList<GRBVar> variableList,
            Polynomial<GRBVar> linearPoly, VariableType coeffVarType = VariableType.BINARY,
            VariableType varType = VariableType.CONTINUOUS)
        {
            throw new Exception("not implemented yet!!!");
        }

        /// <summary>
        /// Wrapper for AddEqZeroConstraint that converts types.
        /// </summary>
        /// <param name="polynomial"></param>
        public string AddEqZeroConstraint(Polynomial<GRBVar> polynomial)
        {
            GRBLinExpr poly = this.convertPolynomialToLinExpr(polynomial);
            string name = this.AddEqZeroConstraint(poly);
            return name;
        }

        /// <summary>
        /// Add a equal to zero constraint (Quadratic).
        /// Following constraints; A * B + C == 0.
        /// </summary>
        public string AddEqZeroConstraint(IList<Polynomial<GRBVar>> coeffPolyList, IList<GRBVar> variableList,
            Polynomial<GRBVar> linearPoly, VariableType coeffVarType = VariableType.BINARY,
            VariableType varType = VariableType.CONTINUOUS)
        {
            throw new Exception("not implemented yet!!!");
        }

        /// <summary>
        /// Add a equal to zero constraint.
        /// </summary>
        /// <param name="polynomial">The polynomial.</param>
        public string AddEqZeroConstraint(GRBLinExpr polynomial)
        {
            string name = "eq_index_" + this._constraintEq.Count;
            this._model.AddConstr(polynomial, GRB.EQUAL,
                (Double)0, name);
            this._constraintEq.Add(polynomial);
            return name;
        }
        /// <summary>
        /// Wrapper that convers the new types to guroubi types and then
        /// calls the proper function.
        /// </summary>
        /// <param name="polynomial1"></param>
        /// <param name="polynomial2"></param>
        public void AddOrEqZeroConstraint(Polynomial<GRBVar> polynomial1, Polynomial<GRBVar> polynomial2)
        {
            GRBLinExpr poly1 = this.convertPolynomialToLinExpr(polynomial1);
            GRBLinExpr poly2 = this.convertPolynomialToLinExpr(polynomial2);
            GRBLinExpr poly2Neg = this.convertPolynomialToLinExpr(polynomial2.Negate());
            // this.AddOrEqZeroConstraint(poly1, poly2);

            var alpha = this._model.AddVar(0.0, 1.0, 0.0, GRB.BINARY, "binary_" + this._binaryVars.Count);
            // var alpha = this._model.AddVar(0.0, 1.0, 0.0, GRB.CONTINUOUS, "binary_" + this._binaryVars.Count);
            this._binaryVars.Add(alpha);
            // this._objective.AddTerm(1 / (this._varBounds), alpha);
            poly1.AddTerm(-1 * this._varBounds / this._scaleFactor, alpha);
            poly2.AddTerm(this._varBounds / this._scaleFactor, alpha);
            poly2.AddConstant(-1 * this._varBounds / this._scaleFactor);
            poly2Neg.AddTerm(this._varBounds / this._scaleFactor, alpha);
            poly2Neg.AddConstant(-1 * this._varBounds / this._scaleFactor);
            this.AddLeqZeroConstraint(poly1);
            this.AddLeqZeroConstraint(poly2);
            this.AddLeqZeroConstraint(poly2Neg);
        }
        /// <summary>
        /// Add or equals zero.
        /// We currently are using SOS
        /// constraints to encode this.
        /// todo: explore auxilary vars.
        /// </summary>
        /// <param name="polynomial1">The first polynomial.</param>
        /// <param name="polynomial2">The second polynomial.</param>
        public void AddOrEqZeroConstraintV1(GRBLinExpr polynomial1, GRBLinExpr polynomial2)
        {
            // Create an auxilary variable for each polynomial
            // Add it to the list of auxilary variables.
            var var_1 = this._model.AddVar(
                    -1 * Math.Pow(10, 10), Math.Pow(10, 10), 0, GRB.CONTINUOUS, "aux_" + this._auxilaryVars.Count);
            this._auxiliaryVarNames.Add("aux_" + this._auxilaryVars.Count);
            this._auxilaryVars.Add(var_1);
            var var_2 = this._model.AddVar(
                    -1 * Math.Pow(10, 10), Math.Pow(10, 10), 0, GRB.CONTINUOUS, "aux_" + this._auxilaryVars.Count);
            this._auxiliaryVarNames.Add("aux_" + this._auxilaryVars.Count);
            this._auxilaryVars.Add(var_2);
            GRBVar[] auxilaries = new GRBVar[] { var_1, var_2 };

            // Create constraints that ensure the auxilary variables are equal
            // to the value of the polynomials.
            polynomial1 = new GRBLinExpr(polynomial1);
            polynomial1.AddTerm(-1, var_1);
            polynomial2 = new GRBLinExpr(polynomial2);
            polynomial2.AddTerm(-1, var_2);
            this.AddEqZeroConstraint(polynomial1);
            this.AddEqZeroConstraint(polynomial2);
            // Add SOS constraint.
            this._model.AddSOS(auxilaries, auxilaries.Select((x, i) => (Double)i).ToArray(),
                        GRB.SOS_TYPE1);
            this._SOSauxilaries.Add(auxilaries);
        }

        /// <summary>
        /// Add a = max(b, c) constraint.
        /// </summary>
        public void AddMaxConstraint(GRBVar LHS, Polynomial<GRBVar> maxItem1, Polynomial<GRBVar> maxItem2) {
            throw new Exception("Not implemented yet.");
        }

        /// <summary>
        /// Add a = max(b, constant) constraint.
        /// </summary>
        public void AddMaxConstraint(GRBVar LHS, Polynomial<GRBVar> var1, double constant) {
            throw new Exception("Not implemented yet.");
        }

        /// <summary>
        /// Add a = max(b, constant) constraint.
        /// </summary>
        public void AddMaxConstraint(GRBVar LHS, GRBVar var1, double constant) {
            throw new Exception("Not implemented yet");
        }

        /// <summary>
        /// Add a = max(b, c) constraint.
        /// </summary>
        public void AddMaxConstraint(GRBVar LHS, GRBVar var1, GRBVar var2) {
            throw new Exception("Not implemented yet");
        }

        /// <summary>
        /// Logistic constraint y = 1/(1 + exp(-x)).
        /// </summary>
        public void AddLogisticConstraint(GRBVar xVar, GRBVar yVar, string name, double FuncPieces = -1, double FuncPeiceError = 0.01,
            double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
        {
            throw new Exception("Not Implemented yet.");
        }

        /// <summary>
        /// power constraint y = x^a.
        /// </summary>
        public void AddPowerConstraint(GRBVar xVar, GRBVar yVar, int a, string name, double FuncPieces = -1, double FuncPeiceError = 0.01,
            double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
        {
            throw new Exception("Not implemented yet....");
        }

        /// <summary>
        /// polynomial constraint y = p0 x^d + p1 x^{d-1} + ... + pd.
        /// </summary>
        public void AddPolynomialConstraint(GRBVar xVar, GRBVar yVar, double[] p, string name, double FuncPieces = -1, double FuncPeiceError = 0.01,
            double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
        {
            throw new Exception("Not implemented yet....");
        }

        /// <summary>
        /// polynomial constraint y = norm_d(x_1, ..., x_n).
        /// </summary>
        public void AddNormConstraint(GRBVar[] xVar, GRBVar yVar, double which, string name, double FuncPieces = -1, double FuncPeiceError = 0.01,
            double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
        {
            throw new Exception("Not implemented yet....");
        }

        /// <summary>
        /// Remove a constraint.
        /// </summary>
        /// <param name="constraintName">name of the constraint in the string format.</param>
        public void RemoveConstraint(string constraintName)
        {
            this._model.Remove(this._model.GetConstrByName(constraintName));
        }

        /// <summary>
        /// Change constraint's RHS.
        /// </summary>
        /// <param name="constraintName">name of the constraint in the string format.</param>
        /// <param name="newRHS">new RHS of the constraint.</param>
        public void ChangeConstraintRHS(string constraintName, double newRHS)
        {
            this._model.GetConstrByName(constraintName).Set(GRB.DoubleAttr.RHS, newRHS);
        }

        /// <summary>
        /// Combine the constraints and variables of another solver into this one.
        /// </summary>
        /// <param name="otherSolver">The other solver.</param>
        public void CombineWith(ISolver<GRBVar, GRBModel> otherSolver)
        {
            // removed support for this. Check earlier git commits if you need it.
        }

        /// <summary>
        /// Call the model update to apply new constraints and objectives.
        /// </summary>
        public void ModelUpdate()
        {
            this._model.Update();
        }

        /// <summary>
        /// Maximize the objective.
        /// </summary>
        /// <returns>A solution.</returns>
        public GRBModel Maximize()
        {
            Console.WriteLine("in maximize call");
            Console.WriteLine("tolerance is : " + this._model.Get(GRB.DoubleParam.IntFeasTol));
            this._model.Set(GRB.DoubleParam.IntFeasTol, 1.0 / this._tolerance);
            // this._model.Parameters.OptimalityTol = 1.0 / this._varBounds;
            this._model.SetObjective(this._objective, GRB.MAXIMIZE);
            this._model.Optimize();
            this._modelRun = true;
            this._model.Write("model_" +  DateTime.Now.Millisecond + ".lp");
            return this._model;
        }

        /// <summary>
        /// Maximize a quadratic objective with objective as input.
        /// reset the callback timer.
        /// </summary>
        /// <returns>A solution.</returns>
        public GRBModel MaximizeQuadPow2(IList<Polynomial<GRBVar>> quadObjective, IList<double> quadCoeff, Polynomial<GRBVar> linObjective, bool reset = false) {
            throw new Exception("not implemented!");
        }

        /// <summary>
        /// Maximize the objective with objective as input.
        /// </summary>
        /// <returns>A solution.</returns>
        public virtual GRBModel Maximize(Polynomial<GRBVar> objective) {
            SetObjective(objective);
            return Maximize();
        }

        /// <summary>
        /// Reset the timer and then maximize.
        /// </summary>
        public virtual GRBModel Maximize(Polynomial<GRBVar> objective, bool reset)
        {
            throw new Exception("this part should be reimplemented based on GurobiSoS");
        }

        /// <summary>
        /// Maximize the objective with objective as input.
        /// </summary>
        /// <returns>A solution.</returns>
        public virtual GRBModel Maximize(GRBVar objective)
        {
            SetObjective(objective);
            return Maximize();
        }

        /// <summary>
        /// find the top $k$ solutions.
        /// </summary>
        public virtual GRBModel Maximize(Polynomial<GRBVar> objective, bool reset, int solutionCount)
        {
            if (solutionCount > 1) {
                this._model.Parameters.PoolSearchMode = 2;
                this._model.Parameters.PoolSolutions = solutionCount;
            }
            return Maximize(objective, reset);
        }

        /// <summary>
        /// check feasibility.
        /// </summary>
        public GRBModel CheckFeasibility(double objectiveValue)
        {
            throw new Exception("this part should be reimplemented based GurobiSoS");
            // Console.WriteLine("in feasibility call");
            // Console.WriteLine("tolerance is : " + this._model.Get(GRB.DoubleParam.IntFeasTol));
            // this._model.Set(GRB.DoubleParam.IntFeasTol, 1.0 / this._tolerance);
            // this._model.Optimize();
            // this._modelRun = true;
            // this._model.Write("model_" +  DateTime.Now.Millisecond + ".lp");
            // return this._model;
        }

        /// <summary>
        /// Get the resulting value assigned to a variable.
        /// </summary>
        /// <returns>The value as a double.</returns>
        public double GetVariable(GRBModel solution, GRBVar variable, int solutionNumber = 0)
        {
            if (!this._modelRun)
            {
                Console.WriteLine("WARNING!: In getVariable and solver had not been called");
            }
            int status = _model.Status;
            if (status == GRB.Status.INFEASIBLE || status == GRB.Status.INF_OR_UNBD)
            {
                throw new Exception("The model cannot be solved because it is infeasible");
            }
            if (status == GRB.Status.UNBOUNDED)
            {
                throw new Exception("The model cannot be solved because it is unbounded");
            }
            if (status != GRB.Status.OPTIMAL)
            {
                throw new Exception("Optimization was stopped with status " + status);
            }
            if (solutionNumber >= this._model.SolCount)
            {
                throw new Exception("solutionNumber should be less than or" +
                    "to the number of available solutions");
            }

            double variableValue = 0.0;
            if (solution.Status != GRB.Status.OPTIMAL) {
                variableValue = variable.Xn;
            } else if (solutionNumber > 0) {
                this._model.Parameters.SolutionNumber = solutionNumber;
                variableValue = variable.Xn;
                this._model.Parameters.SolutionNumber = 0;
            } else {
                variableValue = variable.X;
            }
            return variableValue;
        }

        /// <summary>
        /// Get the resulting value assigned to a variable.
        /// </summary>
        public double GetDualVariable(GRBModel solution, string constraintName) {
            if (solution.Status != GRB.Status.USER_OBJ_LIMIT & solution.Status != GRB.Status.TIME_LIMIT
                & solution.Status != GRB.Status.OPTIMAL & solution.Status != GRB.Status.INTERRUPTED)
            {
                throw new Exception("can't read status since model is not optimal");
            }
            return this._model.GetConstrByName(constraintName).Pi;
        }

        /// <summary>
        /// initialize some of the variables.
        /// </summary>
        public void InitializeVariables(GRBVar variable, double value)
        {
            throw new Exception("Not implemented yet.");
        }

        /// <summary>
        /// adding some auxiliary term to be added to the global objective when maximized.
        /// </summary>
        public void AddGlobalTerm(Polynomial<GRBVar> auxObjPoly)
        {
            throw new Exception("Not implemented yet.");
        }
        /// <summary>
        /// writes the model to a file.
        /// </summary>
        /// <param name="location"></param>
        public virtual void WriteModel(string location)
        {
            this._model.Write($"{location}\\model_" + DateTime.Now.Millisecond + ".lp");
        }
    }
}