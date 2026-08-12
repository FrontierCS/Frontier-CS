// <copyright file="ISolver.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    using System.Diagnostics;
    using System.Linq;
    using Gurobi;
    using ZenLib;
    using ZenLib.ModelChecking;

    /// <summary>
    /// An interface for an optimization solver.
    /// </summary>
    public class SolverZen : ISolver<Zen<Real>, ZenSolution>
    {
        private int precision = 100;
        /// <summary>
        /// This is the objective function.
        /// </summary>
        protected Polynomial<Zen<Real>> _objective = null;

        /// <summary>
        /// The solver constraints.
        /// </summary>
        public IList<Zen<bool>> ConstraintExprs = new List<Zen<bool>>();

        /// <summary>
        /// The solver variables.
        /// </summary>
        public ISet<Zen<Real>> Variables = new HashSet<Zen<Real>>();

        /// <summary>
        /// Static constructor.
        /// </summary>
        static SolverZen()
        {
            ZenSettings.UseLargeStack = true;
        }

        /// <summary>
        /// get model.
        /// </summary>
        public ZenSolution GetModel()
        {
            throw new Exception("need to be implemented");
        }

        /// <summary>
        /// Reset the solver by removing all the variables and constraints.
        /// </summary>
        public void CleanAll(double timeout = -1, bool disableStoreProgress = false)
        {
            ConstraintExprs = new List<Zen<bool>>();
            Variables = new HashSet<Zen<Real>>();
            _objective = null;
        }
        /// <summary>
        /// Getting the timeout value.
        /// </summary>
        public double GetTimeout()
        {
            throw new Exception("Havent yet added this functionality.");
        }
        /// <summary>
        /// Reset the solver by removing all the variables and constraints.
        /// </summary>
        public void CleanAll(bool focusBstBd, double timeout = -1)
        {
            throw new Exception("not implemented yet");
        }

        /// <summary>
        /// append as the next line of the store progress file.
        /// </summary>
        public void AppendToStoreProgressFile(double time_ms, double gap, bool reset = false)
        {
            throw new Exception("not implemented yet");
        }

        /// <summary>
        /// set the timeout.
        /// </summary>
        /// <param name="timeout">value for timeout.</param>
        public void SetTimeout(double timeout)
        {
            throw new Exception("have not implemented yet");
        }

        /// <summary>
        /// set the FocusBstBd.
        /// </summary>
        public void SetFocusBstBd(bool focusBstBd)
        {
            throw new Exception("have not implemented yet");
        }

        /// <summary>
        /// Create a new variable with a given name.
        /// </summary>
        /// <param name="name">The variable name.</param>
        /// <param name="type">The variable type.</param>
        /// <param name="lb">The lb on the variable.</param>
        /// <param name="ub">The ub on the variable.</param>
        /// <returns>The solver variable.</returns>
        /// TODO: why is the default variable type GRB.Continuous for a Zen variable?
        public Zen<Real> CreateVariable(string name, char type = GRB.CONTINUOUS,
            double lb = double.NegativeInfinity, double ub = double.PositiveInfinity)
        {
            var variable = Zen.Symbolic<Real>(name);
            switch (type)
            {
                case GRB.CONTINUOUS:
                    break;
                case GRB.BINARY:
                    this.ConstraintExprs.Add(Zen.Or(variable == (Real)0, variable == (Real)1));
                    break;
                case GRB.INTEGER:
                    // TODO: since constr is true, wouldnt this always evaluate to true?
                    Zen<bool> constr = true;
                    Debug.Assert((lb > double.NegativeInfinity) && (ub < double.PositiveInfinity));
                    for (int i = (int)lb; i <= (int)ub; i++)
                    {
                        constr = Zen.Or(constr, variable == (Real)i);
                    }
                    this.ConstraintExprs.Add(constr);
                    break;
                default:
                    throw new Exception("invalid variable type");
            }
            this.Variables.Add(variable);
            if (ub < double.PositiveInfinity)
            {
                this.ConstraintExprs.Add(variable <= new Real((int)(ub * precision), precision));
            }
            if (lb > double.NegativeInfinity)
            {
                this.ConstraintExprs.Add(variable >= new Real((int)(lb * precision), precision));
            }
            return variable;
        }

        /// <summary>
        /// Get the resulting value assigned to a variable.
        /// </summary>
        /// <returns>The value as a double.</returns>
        public double GetVariable(ZenSolution solution, Zen<Real> variable, int solutionNumber = 0)
        {
            if (solutionNumber != 0)
            {
                throw new Exception("not implemented yet");
            }

            var value = solution.Get(variable).ToString();
            var result = value.Split('/');

            if (result.Length == 1)
            {
                return double.Parse(result[0]);
            }
            else
            {
                return double.Parse(result[0]) / double.Parse(result[1]);
            }
        }

        /// <summary>
        /// Get the resulting value assigned to a variable.
        /// </summary>
        public double GetDualVariable(ZenSolution solution, string constraintName)
        {
            throw new Exception("not implemented yet!!!");
        }

        /// <summary>
        /// Add a less than or equal to zero constraint.
        /// </summary>
        /// <param name="polynomial">The polynomial.</param>
        public string AddLeqZeroConstraint(Polynomial<Zen<Real>> polynomial)
        {
            this.ConstraintExprs.Add(polynomial.AsZen() <= (Real)0);
            return "dummyName";
        }

        /// <summary>
        /// Add a less than or equal to zero constraint (Quadratic).
        /// Following constraints; A * B + C \leq 0.
        /// </summary>
        public string AddLeqZeroConstraint(IList<Polynomial<Zen<Real>>> coeffPolyList, IList<Zen<Real>> variableList,
            Polynomial<Zen<Real>> linearPoly, VariableType coeffVarType = VariableType.BINARY,
            VariableType varType = VariableType.CONTINUOUS)
        {
            throw new Exception("not implemented yet!!!");
        }

        /// <summary>
        /// Add a equal to zero constraint.
        /// </summary>
        /// <param name="polynomial">The polynomial.</param>
        public string AddEqZeroConstraint(Polynomial<Zen<Real>> polynomial)
        {
            this.ConstraintExprs.Add(polynomial.AsZen() == (Real)0);
            return "dummyName";
        }

        /// <summary>
        /// Add a equal to zero constraint (Quadratic).
        /// Following constraints; A * B + C == 0.
        /// </summary>
        /// TODO: add an implementation and test, it seems rather streightforward for zen actually.
        public string AddEqZeroConstraint(IList<Polynomial<Zen<Real>>> coeffPolyList, IList<Zen<Real>> variableList,
            Polynomial<Zen<Real>> linearPoly, VariableType coeffVarType = VariableType.BINARY,
            VariableType varType = VariableType.CONTINUOUS)
        {
            throw new Exception("not implemented yet!!!");
        }

        /// <summary>
        /// Add or equals zero.
        /// </summary>
        /// <param name="polynomial1">The first polynomial.</param>
        /// <param name="polynomial2">The second polynomial.</param>
        public void AddOrEqZeroConstraint(Polynomial<Zen<Real>> polynomial1, Polynomial<Zen<Real>> polynomial2)
        {
            var p1 = polynomial1.AsZen();
            var p2 = polynomial2.AsZen();
            this.ConstraintExprs.Add(Zen.Or(p1 == (Real)0, p2 == (Real)0));
        }

        /// <summary>
        /// Add a = max(b, c) constraint.
        /// </summary>
        /// TODO: add implementation, seems relatively simple?
        public void AddMaxConstraint(Zen<Real> LHS, Polynomial<Zen<Real>> maxItem1, Polynomial<Zen<Real>> maxItem2)
        {
            throw new Exception("Not implemented yet....");
        }

        /// <summary>
        /// Add a = max(b, constant) constraint.
        /// </summary>
        /// TODO: add
        public void AddMaxConstraint(Zen<Real> LHS, Zen<Real> var1, double constant)
        {
            throw new Exception("Not implemented yet");
        }

        /// <summary>
        /// Add a = max(b, constant) constraint.
        /// </summary>
        /// TODO: add
        public void AddMaxConstraint(Zen<Real> LHS, Zen<Real> var1, Zen<Real> var2)
        {
            throw new Exception("Not implemented yet");
        }

        /// <summary>
        /// Add a = max(b, constant) constraint.
        /// </summary>
        /// TODO: add
        public void AddMaxConstraint(Zen<Real> LHS, Polynomial<Zen<Real>> var1, double constant)
        {
            throw new Exception("Not implemented yet.");
        }

        /// <summary>
        /// Logistic constraint y = 1/(1 + exp(-x)).
        /// </summary>
        /// TODO: add.
        public void AddLogisticConstraint(Zen<Real> xVar, Zen<Real> yVar, string name, double FuncPieces = -1, double FuncPeiceError = 0.01,
            double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
        {
            throw new Exception("Not implemented yet....");
        }

        /// <summary>
        /// power constraint y = x^a.
        /// </summary>
        /// TODO: add
        public void AddPowerConstraint(Zen<Real> xVar, Zen<Real> yVar, int a, string name, double FuncPieces = -1, double FuncPeiceError = 0.01,
            double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
        {
            throw new Exception("Not implemented yet....");
        }

        /// <summary>
        /// polynomial constraint y = p0 x^d + p1 x^{d-1} + ... + pd.
        /// </summary>
        /// TODO:add
        public void AddPolynomialConstraint(Zen<Real> xVar, Zen<Real> yVar, double[] p, string name, double FuncPieces = -1, double FuncPeiceError = 0.01,
            double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
        {
            throw new Exception("Not implemented yet....");
        }

        /// <summary>
        /// polynomial constraint y = norm_d(x_1, ..., x_n).
        /// </summary>
        /// TODO: add
        public void AddNormConstraint(Zen<Real>[] xVar, Zen<Real> yVar, double which, string name, double FuncPieces = -1, double FuncPeiceError = 0.01,
            double FuncPieceLength = 0.01, double FuncPieceRatio = -1.0)
        {
            throw new Exception("Not implemented yet....");
        }

        /// <summary>
        /// Remove a constraint.
        /// </summary>
        /// <param name="constraintName">name of the constraint in the string format.</param>
        /// TODO: add
        public void RemoveConstraint(string constraintName)
        {
            throw new Exception("Not Implemented yet....");
        }

        /// <summary>
        /// Change constraint's RHS.
        /// </summary>
        /// <param name="constraintName">name of the constraint in the string format.</param>
        /// <param name="newRHS">new RHS of the constraint.</param>
        /// TODO: add
        public void ChangeConstraintRHS(string constraintName, double newRHS)
        {
            throw new Exception("Not Implemented yet....");
        }

        /// <summary>
        /// Combine the constraints and variables of another solver into this one.
        /// </summary>
        /// <param name="otherSolver">The other solver.</param>
        /// TODO: I think we decided to remove this? double ceck and remove.
        public void CombineWith(ISolver<Zen<Real>, ZenSolution> otherSolver)
        {
            if (otherSolver is SolverZen s)
            {
                foreach (var variable in s.Variables)
                {
                    this.Variables.Add(variable);
                }

                foreach (var constraint in s.ConstraintExprs)
                {
                    this.ConstraintExprs.Add(constraint);
                }
            }
            else
            {
                throw new System.Exception("Can not mix solvers");
            }
        }

        /// <summary>
        /// Call the model update to apply new constraints and objectives.
        /// </summary>
        /// TODO: add.
        public void ModelUpdate()
        {
            throw new Exception("not implemented!");
        }

        /// <summary>
        /// Set the objective polynomial in the internal variable that tracks it.
        /// </summary>
        /// <param name="objective">The solver solution.</param>
        public void SetObjective(Polynomial<Zen<Real>> objective)
        {
            this._objective = objective;
        }

        /// <summary>
        /// Set the objective polynomial in the internal variable that tracks it.
        /// </summary>
        /// <param name="objective">The solver solution.</param>
        public void SetObjective(Zen<Real> objective)
        {
            this._objective = new Polynomial<Zen<Real>>(new Term<Zen<Real>>(1, objective));
        }

        /// <summary>
        /// Maximize the objective.
        /// </summary>
        /// <returns>A solution.</returns>
        public ZenSolution Maximize()
        {
            if (this._objective.ToString() == "dummy")
            {
                return Zen.Solve(Zen.And(this.ConstraintExprs.ToArray()));
            }

            return Zen.Maximize(this._objective.AsZen(), subjectTo: Zen.And(this.ConstraintExprs.ToArray()));
        }

        /// <summary>
        /// Reset the timer and then maximize.
        /// </summary>
        public virtual ZenSolution Maximize(Polynomial<Zen<Real>> objective, bool reset)
        {
            // if (reset) {
            //     throw new Exception("this part should be implemented!!");
            // }
            SetObjective(objective);
            return Maximize();
        }

        /// <summary>
        /// find the top $k$ solutions.
        /// </summary>
        /// TODO: add.
        public virtual ZenSolution Maximize(Polynomial<Zen<Real>> objective, bool reset, int solutionCount)
        {
            throw new Exception("Not implemented yet.");
        }

        /// <summary>
        /// Maximize the objective with objective as input.
        /// </summary>
        /// <returns>A solution.</returns>
        /// TODO: with this function and the ones bellow it, write a better comment that differentiates between it and the others.
        public virtual ZenSolution Maximize(Polynomial<Zen<Real>> objective)
        {
            SetObjective(objective);
            return Maximize();
        }

        /// <summary>
        /// Maximize the objective with objective as input.
        /// </summary>
        /// <returns>A solution.</returns>
        public virtual ZenSolution Maximize(Zen<Real> objective)
        {
            SetObjective(objective);
            return Maximize();
        }

        /// <summary>
        /// Maximize a quadratic objective with objective as input.
        /// reset the callback timer.
        /// </summary>
        /// <returns>A solution.</returns>
        public ZenSolution MaximizeQuadPow2(IList<Polynomial<Zen<Real>>> quadObjective, IList<double> quadCoeff, Polynomial<Zen<Real>> linObjective, bool reset = false)
        {
            throw new Exception("not implemented!");
        }

        /// <summary>
        /// Check whether we can find a feasible solution given the constraints.
        /// </summary>
        public ZenSolution CheckFeasibility(double objectiveValue)
        {
            return Zen.Solve(Zen.And(this.ConstraintExprs.ToArray()));
        }

        /// <summary>
        /// initialize some of the variables.
        /// </summary>
        public void InitializeVariables(Zen<Real> variable, double value)
        {
            throw new Exception("Not implemented yet.");
        }

        /// <summary>
        /// adding some auxiliary term to be added to the global objective when maximized.
        /// </summary>
        public void AddGlobalTerm(Polynomial<Zen<Real>> auxObjPoly)
        {
            throw new Exception("Not implemented yet.");
        }
        /// <summary>
        /// writes the model to a file.
        /// </summary>
        /// <param name="location"></param>
        public virtual void WriteModel(string location)
        {
            throw new Exception("not implemented yet.");
        }
    }
}
