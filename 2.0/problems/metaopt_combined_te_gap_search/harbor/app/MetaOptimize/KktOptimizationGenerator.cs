// <copyright file="KktOptimizationGenerator.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System.Collections.Generic;
    using System.Linq;
    using ZenLib;

    /// <summary>
    /// An optimization encoder that automatically derives the KKT conditions.
    /// TODO: change the name of the file to match the name of the class.
    /// </summary>
    public class KKTRewriteGenerator<TVar, TSolution>
    {
        /// <summary>
        /// The solver being used.
        /// </summary>
        protected internal ISolver<TVar, TSolution> solver;

        /// <summary>
        /// The constraints for polynomial less than or equal to zero.
        /// </summary>
        protected internal IList<Polynomial<TVar>> leqZeroConstraints;

        /// <summary>
        /// The constraints for polynomial equals zero.
        /// </summary>
        protected internal IList<Polynomial<TVar>> eqZeroConstraints;

        /// <summary>
        /// The constructed lambda variables for the KKT conditions.
        /// </summary>
        /// TODO: describe what lambda variables are created for.
        private IList<TVar> lambdaVariables;

        /// <summary>
        /// The constructed nu variables for the KKT conditions.
        /// </summary>
        /// TODO: describe what nu variables are created for.
        private IList<TVar> nuVariables;

        /// <summary>
        /// The variables in the encoding.
        /// </summary>
        public ISet<TVar> Variables;

        /// <summary>
        /// The variables to consider constant for the optimization (avoid derivative).
        /// </summary>
        public ISet<TVar> constantVariables;

        /// <summary>
        /// Creates a new instance of the <see cref="KKTRewriteGenerator{TVar, TSolution}"/> class.
        /// note that we currently only support linear objectives and constraints when we do kkt rewrites, but the concept is more
        /// general and in theory we can support other types as well.
        /// </summary>
        /// <param name="variables">The encoding variables.</param>
        /// <param name="constVariables">The variables to avoid the deriviatve for.</param>
        /// <param name="solver">The solver.</param>
        public KKTRewriteGenerator(ISolver<TVar, TSolution> solver, ISet<TVar> variables, ISet<TVar> constVariables)
        {
            this.Variables = variables;
            this.solver = solver;
            this.leqZeroConstraints = new List<Polynomial<TVar>>();
            this.eqZeroConstraints = new List<Polynomial<TVar>>();
            this.lambdaVariables = new List<TVar>();
            this.nuVariables = new List<TVar>();
            this.constantVariables = constVariables;
        }

        /// <summary>
        /// Add a variable to the set of constant variables.
        /// </summary>
        public void AddConstantVar(TVar variable)
        {
            this.constantVariables.Add(variable);
        }

        /// <summary>
        /// Add a constraint that a polynomial is less than or equal to zero.
        /// </summary>
        /// <param name="polynomial">The polynomial.</param>
        public void AddLeqZeroConstraint(Polynomial<TVar> polynomial)
        {
            this.leqZeroConstraints.Add(polynomial);
        }

        /// <summary>
        /// Add a constraint that a polynomial is equal to zero.
        /// </summary>
        /// <param name="polynomial">The polynomial.</param>
        public void AddEqZeroConstraint(Polynomial<TVar> polynomial)
        {
            this.eqZeroConstraints.Add(polynomial);
        }

        /// <summary>
        /// Get the constraints for the encoding.
        /// </summary>
        /// <returns>The result as a Zen boolean expression.</returns>
        public void AddConstraints()
        {
            foreach (var leqZeroConstraint in this.leqZeroConstraints)
            {
                this.solver.AddLeqZeroConstraint(leqZeroConstraint);
            }

            foreach (var eqZeroConstraint in this.eqZeroConstraints)
            {
                this.solver.AddEqZeroConstraint(eqZeroConstraint);
            }
        }

        /// <summary>
        /// Get the KKT constraints for maximal solution.
        /// The function internally calls add minimization constraints but
        /// first negates the objective function to turn it into a minimization problem.
        /// </summary>
        /// <returns>The result as a Zen boolean expression.</returns>
        public void AddMaximizationConstraints(Polynomial<TVar> objective, bool noKKT = false, bool verbose = false)
        {
            this.AddMinimizationConstraints(objective.Negate(), noKKT, verbose);
        }

        /// <summary>
        /// Get the KKT constraints for minimal solution.
        /// </summary>
        /// <returns>The result as a Zen boolean expression.</returns>
        /// TODO: describe the inputs + describe the output as well, i dont think this function returns anything... so
        /// The description is currently incorrect.
        public virtual void AddMinimizationConstraints(Polynomial<TVar> objective, bool noKKT, bool verbose = false)
        {
            Utils.logger("using KKT encoding", verbose, Utils.LogState.WARNING);
            foreach (var leqZeroConstraint in this.leqZeroConstraints)
            {
                this.solver.AddLeqZeroConstraint(leqZeroConstraint);
            }

            foreach (var eqZeroConstraint in this.eqZeroConstraints)
            {
                this.solver.AddEqZeroConstraint(eqZeroConstraint);
            }

            if (!noKKT)
            {
                Dictionary<int, int> haveLambda = new Dictionary<int, int>();
                for (int i = 0; i < this.leqZeroConstraints.Count; i++)
                {
                    var leqConstraint = this.leqZeroConstraints[i];
                    // For the inner problem, the variables in the outer problem are constants.
                    // This means that they should not be considered when taking the derivative (their derivative is 0).
                    if (leqConstraint.isallInSetOrConst(this.constantVariables))
                    {
                        continue;
                    }

                    var lambda = this.solver.CreateVariable("lambda_" + i);
                    haveLambda[i] = lambdaVariables.Count;
                    this.lambdaVariables.Add(lambda);

                    this.solver.AddLeqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(-1, lambda)));
                    this.solver.AddOrEqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(1, lambda)), leqConstraint);
                }
                Dictionary<int, int> haveNu = new Dictionary<int, int>();
                for (int i = 0; i < this.eqZeroConstraints.Count; i++)
                {
                    if (this.eqZeroConstraints[i].isallInSetOrConst(this.constantVariables))
                    {
                        continue;
                    }
                    haveNu[i] = this.nuVariables.Count;
                    this.nuVariables.Add(this.solver.CreateVariable("nu_" + i));
                }

                foreach (var variable in this.Variables)
                {
                    if (this.constantVariables.Contains(variable))
                    {
                        continue;
                    }

                    var deriv = objective.Derivative(variable);
                    var total = new Polynomial<TVar>(new Term<TVar>(deriv));

                    for (int i = 0; i < this.leqZeroConstraints.Count; i++)
                    {
                        if (!haveLambda.ContainsKey(i))
                            continue;
                        var derivative = this.leqZeroConstraints[i].Derivative(variable);
                        total.Add(new Term<TVar>(derivative, this.lambdaVariables[haveLambda[i]]));
                    }

                    for (int i = 0; i < this.eqZeroConstraints.Count; i++)
                    {
                        if (!haveNu.ContainsKey(i))
                            continue;
                        var derivative = this.eqZeroConstraints[i].Derivative(variable);
                        total.Add(new Term<TVar>(derivative, this.nuVariables[haveNu[i]]));
                    }
                    this.solver.AddEqZeroConstraint(total);
                }
            }
        }
    }
}
