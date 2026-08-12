using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection.Metadata.Ecma335;
using System.Runtime.ExceptionServices;
using System.Text;
using System.Threading.Tasks;
using System.Timers;
using Google.OrTools;
using Google.OrTools.LinearSolver;
using Gurobi;
using Microsoft.VisualBasic.FileIO;
using NLog;

namespace MetaOptimize
{
    /// <summary>
    /// Writing the backend for ORTools to use in case we want to have a different solver.
    /// </summary>
    public class ORToolsSolver : ISolver<Variable, Solver>
    {
        private static readonly Logger Logger = LogManager.GetCurrentClassLogger();
        private double _bigM = Math.Pow(10, 5);
        private double _tolerance = Math.Pow(10, -8);
        private double _bestObjective = double.NaN;
        private String dirName = null;
        private String fileName = null;
        private Dictionary<string, Constraint> _allConstraints = new Dictionary<string, Constraint>();
        /// <summary>
        /// List of auxiliary variables for Q.
        /// </summary>
        protected IList<Polynomial<Variable>> auxPolyList = new List<Polynomial<Variable>>();
        /// <summary>
        /// All the variables we have in the problem formulation.
        /// </summary>
        protected Dictionary<string, Variable> _Variables = new Dictionary<string, Variable>();
        /// <summary>
        /// inequality constraints.
        /// </summary>
        protected int _constraintIneqCount = 0;
        /// <summary>
        /// eq constraints.
        /// </summary>
        protected int _constraintEqCount = 0;
        /// <summary>
        /// timeout.
        /// </summary>
        protected double _timeout = 0;
        /// <summary>
        /// verbose.
        /// </summary>
        protected bool _verbose = false;
        /// <summary>
        /// number of threads for gurobi.
        /// </summary>
        protected int _numThreads = 0;
        /// <summary>
        /// ORTools auxiliary variables.
        /// </summary>
        protected Dictionary<string, Variable> _auxiliaryVars = new Dictionary<string, Variable>();
        /// <summary>
        /// The ORTools model.
        /// </summary>
        protected Solver _model = null;
        /// <summary>
        /// This is the linear objective function.
        /// </summary>
        protected Polynomial<Variable> _objective = new Polynomial<Variable>(new Term<Variable>(0));
        /// <summary>
        /// this shows how many seconds should wait before terminating
        /// if best objective does not improve
        /// only applies to MIP.
        /// </summary>
        protected double _timeToTerminateIfNoImprovement = -1;

        /// <summary>
        /// this show whether we want to store the progress in some
        /// file or not.
        /// </summary>
        protected bool _storeProgress = false;

        /// <summary>
        /// file to store the progress (path to the directory).
        /// will consider this only if _storeProgress = true.
        /// </summary>
        protected string _logFileDirname = null;
        /// <summary>
        /// file to store the progress (file name)
        /// will consider this only if _storeProgress = true.
        /// </summary>
        protected string _logFileFilename = null;

        /// <summary>
        /// if set, will focus on improving the best bound instead of current solution.
        /// </summary>
        protected bool _focusedBstBd = false;

        /// <summary>
        /// removes the solver.
        /// </summary>
        public void Delete()
        {
            this._model = null;
        }
        /// <summary>
        /// Ensures model is updated.
        /// </summary>
        public void ModelUpdate()
        {
            Console.WriteLine("Not needed for ORTools.");
        }
        /// <summary>
        /// This doesn't actually set callbacks, but
        /// it is instead going to set the necessary parameters to implement the
        /// equivalent to what we have in the GurobiSoS implementation.
        /// </summary>
        private void SetCallbacks(bool disableStoreProgress = true)
        {
            var fileExtension = Path.GetExtension(this._logFileFilename);
            this._storeProgress = !disableStoreProgress;
            if (this._storeProgress)
            {
                throw new Exception("ORTools implementation currently does not support this.");
            }
        }
        /// <summary>
        /// Returns the timeout for the solver.
        /// </summary>
        /// <returns></returns>
        public double GetTimeout()
        {
            return this._timeout;
        }
        /// <summary>
        /// Initiates the ORTools solver.
        /// </summary>
        public ORToolsSolver(double timeout = double.PositiveInfinity,
                             bool verbose = true, int numThreads = 0,
                             double timeToTerminateNoImprovement = -1,
                             bool recordProgress = false,
                             string logPath = null,
                             bool focusBstBd = false)
            {
                // Mixed integer programming in ORTools.
                this._model = Solver.CreateSolver("SCIP");
                SetCallbacks();
                if (timeout < double.PositiveInfinity)
                {
                    this._model.SetTimeLimit((long)TimeSpan.FromSeconds(timeout).TotalMilliseconds);
                }
                if (this._model == null)
                {
                    throw new Exception("Could not create solver");
                }
                this._timeout = timeout;
                this._verbose = verbose;
                this._numThreads = numThreads;
                // Presolve is enabled by default so not setting it explicitly.
                this._focusedBstBd = focusBstBd;
                if (numThreads < 0)
                {
                    throw new Exception("Number of thresds should either be 0 or positive");
                }
                if (numThreads != 0)
                {
                    this._model.SetNumThreads(numThreads);
                }
                if (this._verbose)
                {
                    this._model.EnableOutput();
                }
                this._timeToTerminateIfNoImprovement = timeToTerminateNoImprovement;
                this._storeProgress = recordProgress;
                if (recordProgress)
                {
                    if (logPath != null)
                    {
                        this._logFileDirname = Path.GetDirectoryName(logPath);
                        this._logFileFilename = Path.GetFileName(logPath);
                    }
                    else
                    {
                        throw new Exception("Log path should not be null if you want to store the progress");
                    }
                }
                // I have not yet set the progressTimer,
                // storeTimer or the stopWatch because I have not yet run the maximize call.
            }
        /// <summary>
        /// Unlike Gurobi, ORTools does not have a dispose functionality. We instead
        /// have to delete the solver and create a new one.
        /// </summary>
        public void CleanAll(double timeout = -1, bool disableStoreProgress = true)
            {
                this._model = Solver.CreateSolver("SCIP");
                if (timeout > 0)
                {
                    this._model.SetTimeLimit((long)TimeSpan.FromSeconds(timeout).TotalMilliseconds);
                    this._timeout = timeout;
                }
                this._constraintIneqCount = 0;
                this._constraintEqCount = 0;
                this._allConstraints = new Dictionary<string, Constraint>();
                this._Variables = new Dictionary<string, Variable>();
                this._auxiliaryVars = new Dictionary<string, Variable>();
                foreach (Variable var in this._model.variables())
                {
                    this._model.Objective().SetCoefficient(var, 0.0);
                }
                this._bestObjective = double.NaN;
                if (this._numThreads != 0)
                {
                    this._model.SetNumThreads(this._numThreads);
                }
                if (this._verbose)
                {
                    this._model.EnableOutput();
                }
                this.auxPolyList = new List<Polynomial<Variable>>();
                SetCallbacks(disableStoreProgress: true);
            }
        /// <summary>
        /// Append at the next line of the store progress file.
        /// </summary>
        /// <param name="time_ms"></param>
        /// <param name="gap"></param>
        /// <param name="reset"></param>
        public void AppendToStoreProgressFile(double time_ms, double gap, bool reset = false)
            {
                this._bestObjective = Math.Max(this._bestObjective, gap);
                Utils.AppendToFile(this.dirName, this.fileName, time_ms + ", " + this._bestObjective);
            }
        /// <summary>
        /// Reset the solver by removing all variables and constraints.
        /// </summary>
        public void CleanAll(bool focusBstBd, double timeout = -1)
            {
                this._focusedBstBd = focusBstBd;
                CleanAll(timeout);
            }
        /// <summary>
        /// Set the timeout value.
        /// </summary>
        /// <param name="timeout"></param>
        public void SetTimeout(double timeout)
            {
                this._timeout = timeout;
            }
        /// <summary>
        /// Set the FocusBstBD.
        /// </summary>
        public void SetFocusBstBd(bool focusBstBd)
            {
                this._focusedBstBd = focusBstBd;
            }
        /// <summary>
        /// get the model.
        /// </summary>
        public Solver GetModel()
            {
                return this._model;
            }
        /// <summary>
        /// Creates a variable with the given name.
        /// We use the gurobi types here to define type just so that,
        /// we don't have to change any of our other code that is heavily based on gurobi.
        /// </summary>
        public Variable CreateVariable(string name, char type = GRB.CONTINUOUS, double lb = double.NegativeInfinity, double ub = double.PositiveInfinity)
            {
                if (name == null || name.Length == 0)
                {
                    throw new Exception("The variables must have a unique name");
                }
                var new_name = $"{name}_{this._Variables.Count}";
                if (type == GRB.CONTINUOUS)
                {
                    var variable = this._model.MakeNumVar(lb, ub, new_name);
                    this._Variables.Add(new_name, variable);
                    return variable;
                }
                if (type == GRB.INTEGER)
                {
                    var variable = this._model.MakeIntVar(lb, ub, new_name);
                    this._Variables.Add(new_name, variable);
                    return variable;
                }
                if (type == GRB.BINARY)
                {
                    var variable = this._model.MakeBoolVar(new_name);
                    this._Variables.Add(new_name, variable);
                    return variable;
                }
                throw new Exception("Did not recognize the variable type");
            }
        /// <summary>
        /// Creates a continuous variable with the given name.
        /// </summary>
        public Variable CreateContinuousVariable(string name, double lb = double.NegativeInfinity, double ub = double.PositiveInfinity)
            {
                return CreateVariable(name, GRB.CONTINUOUS, lb, ub);
            }
        /// <summary>
        /// Creates a binary variable.
        /// Notice that we use gurobi type indicators internally just to
        /// avoid specifying new Enums etc.
        /// </summary>
        public Variable CreateBinaryVariable(string name)
            {
                return this.CreateVariable(name, type: GRB.BINARY);
            }
        /// <summary>
        /// Creates an integer variable.
        /// </summary>
        public Variable CreateIntegerVariable(string name, double lb = double.NegativeInfinity, double ub = double.PositiveInfinity)
            {
                return this.CreateVariable(name, type: GRB.INTEGER, lb: lb, ub: ub);
            }
        /// <summary>
        /// Sets the optimization objective.
        /// </summary>
        public void SetObjective(Polynomial<Variable> objective)
            {
                this._objective = objective;
            }
        /// <summary>
        /// Sets the optimization objective to this variable.
        /// </summary>
        /// <param name="objective"></param>
        public void SetObjective(Variable objective)
        {
            this._objective = new Polynomial<Variable>(new Term<Variable>(1, objective));
        }
        /// <summary>
        /// Converts a polynomial to a linear expression.
        /// </summary>
        protected internal Constraint SetConstraintToPolynomial(Polynomial<Variable> poly, Constraint constraint)
            {
                var termCoefficients = new Dictionary<Variable, double>();
                double constant = 0;
                foreach (var term in poly.GetTerms())
                {
                    if (term.Variable.IsSome())
                    {
                        if (!termCoefficients.ContainsKey(term.Variable.Value))
                        {
                            termCoefficients[term.Variable.Value] = 0;
                        }
                        termCoefficients[term.Variable.Value] += term.Coefficient;
                    }
                    else
                    {
                        constant += term.Coefficient;
                    }
                }
                foreach (var term in termCoefficients)
                {
                    constraint.SetCoefficient(term.Key, term.Value);
                }
                double currentUB = constraint.Ub();
                double currentLB = constraint.Lb();
                // Remember that the constraints we have are all of the form ax + b \leq 0 or ax + b = 0.
                // Therefore, when I want to add the constants to the bounds, I actually have to negate them.
                constraint.SetUb(currentUB - constant);
                constraint.SetLb(currentLB - constant);
                return constraint;
            }
        /// <summary>
        /// Sets the class variable quadObjective.
        /// It takes as input a list of polynomials, and their corresponding coefficients.
        /// It then returns the sum of the polynomials to the power 2 multiplied by their respective coefficients.
        /// </summary>
        public void SetSumOfPow2PolynomialsToObjective(IList<Polynomial<Variable>> quadObjective, IList<double> quadCoeff)
            {
                var numQuadTerms = quadObjective.Count;
                Debug.Assert(numQuadTerms == quadCoeff.Count());
                for (int i = 0; i < numQuadTerms; i++)
                {
                    ConvertPolyToPower2(quadObjective[i], quadCoeff[i], setObjective: true);
                }
            }
        /// <summary>
        /// quadCoefficient * (a * x + b)^2 = quadCoefficient * (a^2 * x^2 + 2ab * x + b^2).
        /// </summary>
        /// <returns></returns>
        protected internal Constraint ConvertPolyToPower2(Polynomial<Variable> quadPoly, double quadCoeff, Constraint constraint = null, bool setObjective = false)
            {
                if (constraint == null && setObjective == false)
                {
                    throw new Exception("The usage for this function is different for the two use-cases.");
                }
                double b = 0;
                Variable x = null;
                double a = 1;
                foreach (var term in quadPoly.GetTerms())
                {
                    switch (term.Exponent)
                    {
                        case 1:
                            if (setObjective)
                            {
                                throw new Exception("seems like ORTools does not yet support this.");
                                // this._model.Objective().SetQuadraticCoefficient(term.Variable.Value, term.Variable.Value, term.Coefficient * term.Coefficient * quadCoeff);
                            }
                            else
                            {
                                throw new Exception("seems like ORTools does not yet support this.");
                                // constraint.SetQuadraticCoefficient(term.Variable.Value, term.Variable.Value, term.Coefficient * term.Coefficient * quadCoeff);
                            }
                            // a = term.Coefficient;
                            // x = term.Variable.Value;
                            // break;
                        case 0:
                            if (!setObjective)
                            {
                               double currentUB = constraint.Ub();
                               double currentLB = constraint.Lb();
                               // Remember that the constraints we have are all of the form ax + b \leq 0 or ax + b = 0.
                               // Therefore, when I want to add the constants to the bounds, I actually have to negate them.
                               constraint.SetUb(currentUB - term.Coefficient * term.Coefficient * quadCoeff);
                               constraint.SetLb(currentLB - term.Coefficient * term.Coefficient * quadCoeff);
                            }
                            else
                            {
                                this._objective.Add(new Term<Variable>(term.Coefficient * term.Coefficient * quadCoeff));
                                this._model.Objective().SetOffset(term.Coefficient * term.Coefficient * quadCoeff);
                            }
                            b = term.Coefficient;
                            break;
                        default:
                            throw new Exception("The objective function should be linear");
                    }
                }
                if (setObjective)
                {
                    this._objective.Add(new Term<Variable>(2 * a * b * quadCoeff, x));
                    this._model.Objective().SetCoefficient(x, 2 * a * b * quadCoeff);
                }
                else
                {
                    constraint.SetCoefficient(x, 2 * a * b * quadCoeff);
                }
                return constraint;
            }
        /// <summary>
        /// Adds a \leq constraint.
        /// </summary>
        /// <param name="polynomial"></param>
        /// <returns></returns>
        public string AddLeqZeroConstraint(Polynomial<Variable> polynomial)
            {
                this._constraintIneqCount++;
                string name = "ineq_index_" + this._constraintIneqCount;
                var constraint = this._model.MakeConstraint(-double.MaxValue, 0.0, name);
                this._allConstraints[name] = constraint;
                constraint = SetConstraintToPolynomial(polynomial, constraint);
                return name;
            }
        /// <summary>
        /// Have not yet implemented this, but can do if needed.
        /// </summary>
        private Constraint ConvertQEToLinear(IList<Polynomial<Variable>> coeffPolyList, IList<Variable> variableList,
                                             Polynomial<Variable> linearPoly, VariableType varType, Constraint constraint)
            {
                for (int i = 0; i < coeffPolyList.Count; i++)
                {
                    Polynomial<Variable> coeffPoly = coeffPolyList[i];
                    Variable variable = variableList[i];
                    foreach (var term in coeffPoly.GetTerms())
                    {
                        switch (term.Exponent)
                        {
                            case 1:
                                Variable binaryVar = term.Variable.Value;
                                ConvertBinaryMultToLin(constraint, variable, binaryVar, term.Coefficient);
                                break;
                            case 0:
                                linearPoly.Add(term);
                                break;
                            default:
                                throw new Exception("non 0|1 exponent is not modeled!!");
                        }
                    }
                }
                constraint = this.SetConstraintToPolynomial(linearPoly, constraint);
                return constraint;
            }
        /// <summary>
        /// This function onverts a quadratic term in a polynomial into a linear one.
        /// It assumes the quadratic term is a multiplication of a binary variable with another variable.
        /// Here x_i is the binary variable and y_i is the other one.
        /// The function replaces x_i * y_i with aux_i.
        /// It sandwitches aux_i such that -M * x_i \le aux_i \le M * x_i.
        /// and aux_i >= y_i - M(1 - x_i) and aux_i \le y_i + M(1 - x_i).
        /// </summary>
        /// <param name="constraint">The original constraint that contains the multiplicative term.</param>
        /// <param name="variable">The variable that can be continuous, binary, or integer.</param>
        /// <param name="binaryVariable">The binary variable in the multiplication.</param>
        /// <param name="constCoef">The constant coefficient of the multiplicative term.</param>
        private void ConvertBinaryMultToLin(Constraint constraint, Variable variable, Variable binaryVariable, double constCoef)
            {
                var auxVar = this.CreateVariable("aux_qe");
                constraint.SetCoefficient(auxVar, constCoef);

                // X_i = binary variable
                // y_i = the other variable
                // this constraint ensures that the minimum of aux is y_i when x_i = 1.
                var auxConst = new Polynomial<Variable>(new Term<Variable>(-1, variable));
                auxConst.Add(new Term<Variable>(1 * this._bigM));
                auxConst.Add(new Term<Variable>(-1 * this._bigM, binaryVariable));
                auxConst.Add(new Term<Variable>(1, auxVar));
                this.AddLeqZeroConstraint(auxConst.Negate());

                // aux >= -M x_i.
                var auxConst2 = new Polynomial<Variable>(new Term<Variable>(-1, auxVar));
                auxConst2.Add(new Term<Variable>(-1 * this._bigM, binaryVariable));
                this.AddLeqZeroConstraint(auxConst2);

                // aux <= y_i + M(1 - x_i)
                var auxConst3 = new Polynomial<Variable>(new Term<Variable>(-1, variable));
                auxConst3.Add(new Term<Variable>(-1 * this._bigM));
                auxConst3.Add(new Term<Variable>(1 * this._bigM, binaryVariable));
                auxConst3.Add(new Term<Variable>(1, auxVar));
                this.AddLeqZeroConstraint(auxConst3);

                // aux <= M x_i.
                var auxConst4 = new Polynomial<Variable>(new Term<Variable>(1, auxVar));
                auxConst4.Add(new Term<Variable>(-1 * this._bigM, binaryVariable));
                this.AddLeqZeroConstraint(auxConst4);
            }
        private Constraint ConvertQEToQEExpr(IList<Polynomial<Variable>> coeffPolyList,
                                             IList<Variable> variableList,
                                             Polynomial<Variable> linearPoly)
            {
                throw new Exception("We have not yet implemented this function for ORTools");
            }
        private LinearExpr ConvertQESOS(IList<Polynomial<Variable>> coeffPolyList,
                                        IList<Variable> variableList,
                                        Polynomial<Variable> linearPoly)
            {
                throw new Exception("We have not yet implemented this function for ORTools.");
            }
        /// <summary>
        /// Add a less than or equal to zero constraint (quadratic).
        /// Following: A * B + C \leq 0.
        /// But we actually haven't implemented this in ORTools, just adding the building blocks.
        /// </summary>
        /// <returns></returns>
        public string AddLeqZeroConstraint(IList<Polynomial<Variable>> coeffPolyList,
                                               IList<Variable> variableList,
                                               Polynomial<Variable> linearPoly,
                                               VariableType coeffVarType = VariableType.BINARY,
                                               VariableType varType  = VariableType.CONTINUOUS)
            {
                string name = "ineq_index" + this._constraintIneqCount++;
                if (coeffVarType == VariableType.BINARY)
                {
                    var constraint = this._model.MakeConstraint(-double.MaxValue, 0.0, name);
                    constraint = this.ConvertQEToLinear(coeffPolyList, variableList, linearPoly, varType, constraint);
                    this._allConstraints[name] = constraint;
                }
                else
                {
                    throw new Exception("OR Tools is not good at this, use Gurobi.");
                }
                return name;
            }
        /// <summary>
        /// Wrapper for AddEqZeorConstraint that converts types.
        /// </summary>
        /// <param name="polynomial"></param>
        /// <returns></returns>
        public string AddEqZeroConstraint(Polynomial<Variable> polynomial)
            {
                string name = "eq_index_" + this._constraintEqCount++;
                var constraint = this._model.MakeConstraint(0.0, 0.0, name);
                constraint = SetConstraintToPolynomial(polynomial, constraint);
                this._allConstraints[name] = constraint;
                return name;
            }
        /// <summary>
        /// Adds a quadratic \le constraint.
        /// </summary>
        public string AddEqZeroConstraint(IList<Polynomial<Variable>> coeffPolyList,
                                          IList<Variable> variableList,
                                          Polynomial<Variable> linearPoly,
                                          VariableType coeffVarType = VariableType.BINARY,
                                          VariableType varType = VariableType.CONTINUOUS)
            {
                string name = "ineq_index_" + this._constraintEqCount++;
                if (coeffVarType == VariableType.BINARY)
                {
                    Constraint quadConstraint = this._model.MakeConstraint(0.0, 0.0, name);
                    quadConstraint = this.ConvertQEToLinear(coeffPolyList, variableList, linearPoly, varType, quadConstraint);
                    this._allConstraints[name] = quadConstraint;
                }
                else
                {
                    throw new Exception("OR Tools is not good at this, use Gurobi.");
                }
                return name;
            }
        /// <summary>
        /// Combine the constraints and variables of another solver into this one.
        /// </summary>
        /// <param name="otherSolver">The other solver.</param>
        public void CombineWith(ISolver<Variable, Solver> otherSolver)
            {
                throw new Exception("We no longer support combining two solvers.");
            }
        /// <summary>
        /// Ensure at least one of these items is zero.
        /// </summary>
        /// <param name="polynomial1"></param>
        /// <param name="polynomial2"></param>
        public virtual void AddOrEqZeroConstraint(Polynomial<Variable> polynomial1, Polynomial<Variable> polynomial2)
            {
                Logger.Warn("This solver is very sensitive to bigM choice. Make sure to double check your results.");
                // This is going to do A <= Mb.
                var control = this.CreateBinaryVariable("control");
                var expr1PolynomialUB = polynomial1.Copy();
                expr1PolynomialUB.Add(new Term<Variable>(-1 * this._bigM, control));
                this.AddLeqZeroConstraint(expr1PolynomialUB);

                // this is going to do A \geq -Mb => A + Mb \geq 0 => -A-Mb \leq 0.
                var expr1PolynomialLB = polynomial1.Copy().Negate();
                expr1PolynomialLB.Add(new Term<Variable>(-1 * this._bigM, control));
                this.AddLeqZeroConstraint(expr1PolynomialLB);

                // this adds B - (1 - control)M \leq 0.
                var expr2PolynomialUB = polynomial2.Copy();
                expr2PolynomialUB.Add(new Term<Variable>(this._bigM, control));
                expr2PolynomialUB.Add(new Term<Variable>(-1 * this._bigM));
                this.AddLeqZeroConstraint(expr2PolynomialUB);
                // this adds -B - (1 - control)M \leq 0 -> B \ge - (1 - control) M.
                var expr2PolynomialLB = polynomial2.Copy().Negate();
                expr2PolynomialLB.Add(new Term<Variable>(this._bigM, control));
                expr2PolynomialLB.Add(new Term<Variable>(-1 * this._bigM));
                this.AddLeqZeroConstraint(expr2PolynomialLB);
                // this.AddOrEqZeroConstraintV1(this.FromPolyToLinExpr(polynomial1), this.FromPolyToLinExpr(polynomial2));
            }
        /// <summary>
        /// Logistic constraint y = 1/(1 + exp(-x)).
        /// </summary>
        public void AddLogisticConstraint(Variable xVar, Variable yVar, string name, double FuncPieces = -1, double FuncPeicError = 0.01, double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
            {
                throw new Exception("This is not supported for ORTools use Gurobi instead");
            }
        /// <summary>
        /// power constraint y = x^a.
        /// </summary>
        public void AddPowerConstraint(Variable xVar, Variable yVar, int a, string name, double FuncPieces = -1, double FuncPeiceError = 0.01, double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
            {
                throw new Exception("This is not supported for ORTools use Gurobi instead");
            }
        /// <summary>
        /// polynomial constraint y = p0 x^d + p1 x^{d-1} + ... + pd.
        /// </summary>
        public void AddPolynomialConstraint(Variable xVar, Variable yVar, double[] p, string name, double FuncPieces = -1, double FuncPeiceError = 0.01, double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
            {
                throw new Exception("This is not supported for ORTools use Gurobi instead");
            }
        /// <summary>
        /// polynomial constraint y = norm_d(x_1, ..., x_n).
        /// </summary>
        public void AddNormConstraint(Variable[] xVar, Variable yVar, double which, string name, double FuncPieces = -1, double FuncPieceError = 0.01, double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
        {
            throw new Exception("This is not supported for ORTools use Gurobi instead");
        }
        /// <summary>
        /// Add LHS = max(maxItem1, maxItem2).
        /// </summary>
        public void AddMaxConstraint(Variable LHS, Polynomial<Variable> maxItem1, Polynomial<Variable> maxItem2)
            {
                // Create an auxiliary variable for each polynomial.
                var var1 = this.CreateVariable("aux_" + this._auxiliaryVars.Count, lb: Double.NegativeInfinity, ub: double.PositiveInfinity);
                var var2 = this.CreateVariable("aux_" + this._auxiliaryVars.Count, lb: Double.NegativeInfinity, ub: double.PositiveInfinity);

                // Add constraints that set these to be equal to zero.
                var item1Constraint = maxItem1.Copy();
                item1Constraint.Add(new Term<Variable>(-1, var1));
                this.AddEqZeroConstraint(item1Constraint);

                var item2Constraint = maxItem2.Copy();
                item2Constraint.Add(new Term<Variable>(-1, var2));
                this.AddEqZeroConstraint(item2Constraint);
                this.AddMaxConstraint(LHS, var1, var2);
            }
        /// <summary>
        /// Add a = max(b, c) constraints.
        /// To achieve this, the function ensures that b \le a \le b + M * binaryvariable,
        /// and that c \le a \le c + M * (1 - binaryvariable).
        /// </summary>
        public void AddMaxConstraint(Variable LHS, Variable var1, Variable var2)
            {
                // Creates a binary variable.
                var bin = this.CreateBinaryVariable("aux_max");
                // a >= b
                this.AddLeqZeroConstraint(new Polynomial<Variable>(
                    new Term<Variable>(-1, LHS),
                    new Term<Variable>(1, var1)));
                // a >= c
                this.AddLeqZeroConstraint(new Polynomial<Variable>(
                    new Term<Variable>(-1, LHS),
                    new Term<Variable>(1, var2)));
                // a <= b + M * binaryvar
                this.AddLeqZeroConstraint(new Polynomial<Variable>(
                    new Term<Variable>(1, LHS),
                    new Term<Variable>(-1, var1),
                    new Term<Variable>(-1 * this._bigM, bin)));
                // a <= c + M(1 - binaryvar)
                this.AddLeqZeroConstraint(new Polynomial<Variable>(
                    new Term<Variable>(1, LHS),
                    new Term<Variable>(-1, var2),
                    new Term<Variable>(-1 * this._bigM),
                    new Term<Variable>(this._bigM, bin)));
            }
        /// <summary>
        /// Since ORTools does not have a similar to AddGenConstrMax,
        /// So I am going to write my own version.
        /// </summary>
        public void AddMaxConstraint(Variable LHS, Variable var1, double constant)
            {
                // Creates a binary variable.
                var bin = this.CreateBinaryVariable("aux_max");
                // a >= b
                this.AddLeqZeroConstraint(new Polynomial<Variable>(
                    new Term<Variable>(-1, LHS),
                    new Term<Variable>(1, var1)));
                // a >= c
                this.AddLeqZeroConstraint(new Polynomial<Variable>(
                    new Term<Variable>(-1, LHS),
                    new Term<Variable>(1 * constant)));
                // a <= b + M * binaryvar
                this.AddLeqZeroConstraint(new Polynomial<Variable>(
                    new Term<Variable>(1, LHS),
                    new Term<Variable>(-1, var1),
                    new Term<Variable>(-1 * this._bigM, bin)));
                // a <= c + M(1 - binaryvar)
                this.AddLeqZeroConstraint(new Polynomial<Variable>(
                    new Term<Variable>(1, LHS),
                    new Term<Variable>(-1 * constant),
                    new Term<Variable>(-1 * this._bigM),
                    new Term<Variable>(this._bigM, bin)));
            }
        /// <summary>
        /// Add a = max(b, constant) constraint.
        /// </summary>
        public void AddMaxConstraint(Variable LHS, Polynomial<Variable> var1, double constant)
            {
                throw new Exception("Not implemented yet.");
            }
        /// <summary>
        /// Removes a constraint from the solver.
        /// </summary>
        /// <param name="constraintName"></param>
        public void RemoveConstraint(string constraintName)
            {
                // this._model.Remove(this._allConstraints[constraintName]);
                // Set the bounds to non-restrictive values
                this._allConstraints[constraintName].SetBounds(double.NegativeInfinity, double.PositiveInfinity);

                // Iterate over all variables and set their coefficients in the constraint to zero
                foreach (Variable var in this._model.variables())
                {
                    this._allConstraints[constraintName].SetCoefficient(var, 0.0);
                }
            }
        /// <summary>
        /// Change the constraint's RHS.
        /// </summary>
        public void ChangeConstraintRHS(string constraintName, double newRHS)
            {
                if (constraintName.Contains("ineq"))
                {
                    this._allConstraints[constraintName].SetBounds(double.NegativeInfinity, newRHS);
                }
                else if (constraintName.Contains("eq"))
                {
                    this._allConstraints[constraintName].SetBounds(newRHS, newRHS);
                }
                else
                {
                    throw new Exception("Did not recognize the constraint name.");
                }
            }
        /// <summary>
        /// Write the model to a file.
        /// </summary>
        public virtual void WriteModel(string location)
            {
                Directory.CreateDirectory(location);
                var path = Path.Combine(location, "model_" + Utils.GetFID() + DateTime.Now.Millisecond + ".lp");
                string lpModel = this._model.ExportModelAsLpFormat(false);  // false => do not obfuscate names
                File.WriteAllText(path, lpModel);
            }
        /// <summary>
        /// This is because unlike Gurobi in ORTools we cannot set the objective
        /// from a linear expression. So what I am doing instead is I am building the linear,
        /// objective functionand then setting it in the model.
        /// </summary>
        private void SetObjective()
            {
                var termCoefficients = new Dictionary<Variable, double>();
                double constant = 0;
                foreach (var term in this._objective.GetTerms())
                {
                    if (term.Variable.IsSome())
                    {
                        if (!termCoefficients.ContainsKey(term.Variable.Value))
                        {
                            termCoefficients[term.Variable.Value] = 0;
                        }
                        termCoefficients[term.Variable.Value] += term.Coefficient;
                    }
                    else
                    {
                        constant += term.Coefficient;
                    }
                }
                foreach (var term in termCoefficients)
                {
                    this._model.Objective().SetCoefficient(term.Key, term.Value);
                }
                this._model.Objective().SetOffset(constant);
            }
        /// <summary>
        /// Check feasibility of the optimization.
        /// </summary>
        /// <param name="objectiveValue"></param>
        /// <returns></returns>
        public Solver CheckFeasibility(double objectiveValue)
            {
                Console.WriteLine("In ORTools feasibility call");
                SetObjective();
                this._model.Objective().SetMaximization();
                try
                {
                    string modelLp = this._model.ExportModelAsLpFormat(false); // false => do not obfuscate names
                    Directory.CreateDirectory(@"C:\tmp\ortools_dump\");
                    string lpFile = $@"C:\tmp\ortools_dump\model_{DateTime.Now:yyyyMMdd_HHmmss_fff}.lp";
                    File.WriteAllText(lpFile, modelLp);
                    Console.WriteLine($"Model written to {lpFile}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine("Warning: Could not export model. " + ex.Message);
                }

                var resultStatus = this._model.Solve();
                if (resultStatus != Solver.ResultStatus.OPTIMAL &&
                    resultStatus != Solver.ResultStatus.FEASIBLE)
                {
                    throw new InfeasibleOrUnboundSolution();
                }
                double foundObjectiveValue = this._model.Objective().Value();
                if (foundObjectiveValue < objectiveValue)
                {
                    // If the solver's best found solution is below the threshold,
                    // treat it as infeasible for your purpose.
                    throw new InfeasibleOrUnboundSolution();
                }
                return this._model;
            }
        private Solver RunSolverPeriodically()
            {
                double lastObj = double.NegativeInfinity;
                int stableCount = 0;
                int stableLimit = 20000;
                int timeLimit = 1000;
                if (this._storeProgress)
                {
                    throw new Exception("I haven't implemented this, but it is easy to do if you want to.");
                }
                int numIter = 20000;
                if (this._timeToTerminateIfNoImprovement > 0 && this._timeout != 0)
                {
                    numIter = (int)(this._timeout / 1000.0);
                    stableLimit = (int)(this._timeToTerminateIfNoImprovement / 1000.0);
                }
                for (int i = 0; i < numIter; i++)
                {
                    this._model.SetTimeLimit(timeLimit);
                    Solver.ResultStatus resultStatus = this._model.Solve();
                    if (resultStatus == Solver.ResultStatus.OPTIMAL)
                    {
                        return this._model;
                    }
                    if (resultStatus == Solver.ResultStatus.FEASIBLE)
                    {
                        double objValue = this._model.Objective().Value();
                        if (objValue - lastObj < 1e-6)
                        {
                            stableCount++;
                        }
                        else
                        {
                            stableCount = 0;
                        }
                        lastObj = objValue;
                        var variables = new List<Variable>();
                        var values = new List<double>();
                        foreach (var kvp in this._model.variables())
                        {
                            variables.Add(kvp);
                            values.Add(kvp.SolutionValue());
                        }
                        this._model.SetHint(variables.ToArray(), values.ToArray());
                    }
                    else
                    {
                        if (resultStatus == Solver.ResultStatus.INFEASIBLE)
                        {
                            timeLimit *= 2;
                        }
                    }
                }
                return this._model;
            }
        /// <summary>
        /// Runs the optimizer. Notice that we are just doing
        /// a simpler implementation here compared to what we have in Gurobi.
        /// The intent here is to give users more options but we will not actively support this code.
        /// </summary>
        /// <returns></returns>
        public virtual Solver Maximize()
            {
                Console.WriteLine("In maximize Call for ORTools");
                foreach (var auxVar in auxPolyList)
                {
                    this._objective.Add(auxVar);
                }
                SetObjective();
                this._model.Objective().SetMaximization();
                this._model.SetSolverSpecificParametersAsString("numerics/feastol = 1e-9 lp/scaling = TRUE");
                SetCallbacks();
                if (this._storeProgress || this._timeToTerminateIfNoImprovement > 0)
                {
                    Console.WriteLine("WARNING: This is an untested part of the code. Use at your own risk.");
                    return this.RunSolverPeriodically();
                }
                if (this._timeout < double.PositiveInfinity)
                {
                    this._model.SetTimeLimit((int)(this._timeout * 1000));
                }
                // this.WriteModel("C:\\Users\\bearzani\\Desktop\\Behnaz_Work\\wanrisk\\MetaOptimize\\Debug");
                Solver.ResultStatus resultStatus = this._model.Solve();
                if (resultStatus != Solver.ResultStatus.OPTIMAL && resultStatus != Solver.ResultStatus.FEASIBLE)
                {
                    throw new Exception("The solution is infeasible or unbounded.");
                }
                if (resultStatus != Solver.ResultStatus.OPTIMAL && resultStatus != Solver.ResultStatus.FEASIBLE)
                {
                    throw new Exception("We do not have a parse-able solution.");
                }
                return this._model;
            }
        /// <summary>
        /// Reset the timer and then maximize.
        /// </summary>
        public virtual Solver Maximize(Polynomial<Variable> objective, bool reset, int solutionCount)
            {
                return Maximize(objective, reset);
            }
        /// <summary>
        /// Should reset the callbacks but we don't have those in ORTools right now,
        /// and then maximize the objective.
        /// </summary>
        /// <param name="objective"></param>
        /// <param name="reset"></param>
        /// <returns></returns>
        public virtual Solver Maximize(Polynomial<Variable> objective, bool reset = false)
        {
            if (reset)
            {
                Logger.Warn("Because of the way ORTools works we cannot support this right now.");
            }
            return Maximize(objective);
        }
        /// <summary>
        /// Maximizes the objective.
        /// </summary>
        /// <param name="objective"></param>
        /// <returns></returns>
        public virtual Solver Maximize(Polynomial<Variable> objective)
        {
            SetObjective(objective);
            return Maximize();
        }
        /// <summary>
        /// Maximizes the variable that is given.
        /// </summary>
        /// <param name="objective"></param>
        /// <returns></returns>
        public virtual Solver Maximize(Variable objective)
        {
            Polynomial<Variable> objectivePoly = new Polynomial<Variable>(new Term<Variable>(1, objective));
            return Maximize(objectivePoly);
        }
        /// <summary>
        /// Maximizes a quadratic objective.
        /// </summary>
        public Solver MaximizeQuadPow2(IList<Polynomial<Variable>> quadObjective, IList<double> quadCoeff, Polynomial<Variable> listObjective, bool reset = false)
        {
            throw new Exception("Currently do not support power two functions in ORTools use Gurobi instead.");
        }
        /// <summary>
        /// Gets the value the solver computed for a variable.
        /// </summary>
        public double GetVariable(Solver solution, Variable variable, int solutionNumber = 0)
        {
            double variableValue = variable.SolutionValue();
            return variableValue;
        }
        /// <summary>
        /// Did not implement this functionality.
        /// </summary>
        /// <param name="solution"></param>
        /// <param name="constraintName"></param>
        /// <returns></returns>
        public double GetDualVariable(Solver solution, string constraintName)
        {
            throw new Exception("ORTools does not allow us to get constraints by name and so we did not implement this functionality.");
        }
        /// <summary>
        /// Gives the solver a hint about a value of a variable.
        /// </summary>
        /// <param name="variable"></param>
        /// <param name="value"></param>
        public void InitializeVariables(Variable variable, double value)
        {
            this._model.SetHint(new Variable[] { variable }, new double[] { value });
        }
        /// <summary>
        /// adding some auxiliary term to the global objective.
        /// </summary>
        /// <param name="auxObjPoly"></param>
        public void AddGlobalTerm(Polynomial<Variable> auxObjPoly)
        {
            this.auxPolyList.Add(auxObjPoly);
        }
    }
}
