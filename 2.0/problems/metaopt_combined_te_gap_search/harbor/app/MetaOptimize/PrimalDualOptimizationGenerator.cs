// <copyright file="KktOptimizationGenerator.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System.Collections.Generic;
    using System.Threading;

    /// <summary>
    /// An optimization encoder that automatically adds the primal-dual conditions.
    /// </summary>
    /// TODO: do you need the inheritance from the KKTRewritegenerator? if yes, maybe you need a different sub-class which is
    /// rewrite generator that both of these classes inherit from?
    public class PrimalDualRewriteGenerator<TVar, TSolution> : KKTRewriteGenerator<TVar, TSolution>
    {
        private int NumProcesses = -1;
        /// <summary>
        /// Creates a new instance of the <see cref="PrimalDualRewriteGenerator{TVar, TSolution}"/> class.
        /// </summary>
        /// <param name="variables">The encoding variables.</param>
        /// <param name="constVariables">The variables to consider constant for the optimization.</param>
        /// <param name="solver">The solver.</param>
        /// <param name="numProcesses">number of processors to use for PrimalDual constraint computation.</param>
        public PrimalDualRewriteGenerator(ISolver<TVar, TSolution> solver, ISet<TVar> variables, ISet<TVar> constVariables, int numProcesses)
            : base(solver, variables, constVariables)
        {
            this.NumProcesses = numProcesses;
        }

        /// <summary>
        /// Get the primal dual constraints for minimal solution.
        /// </summary>
        // TODO: in the kkt function we call the variables nu and lambda based on boyd's terminology.
        // Here you have dualeq and dualleq variables, we should make the two functions consistant.
        // TODO: add a test case that checks the results from primal dual match the kkt scenario.
        public override void AddMinimizationConstraints(Polynomial<TVar> objective, bool noPrimalDual, bool verbose = false)
        {
            Utils.logger("using primal dual encoding", verbose, Utils.LogState.WARNING);
            // adding primal constraints
            Utils.logger("adding primal constraints", verbose);
            this.AddConstraints();

            if (!noPrimalDual)
            {
                Dictionary<int, TVar> leqDualVariables = new Dictionary<int, TVar>();
                Dictionary<int, TVar> eqDualVariables = new Dictionary<int, TVar>();

                IList<TVar> dualObjectiveTerms = new List<TVar>();
                IList<Polynomial<TVar>> dualObjectiveCoeff = new List<Polynomial<TVar>>();
                Utils.logger("computing dual objective coefficients for inequality constraints.", verbose);
                for (int i = 0; i < leqZeroConstraints.Count; i++)
                {
                    var leqConstraint = this.leqZeroConstraints[i];
                    if (leqConstraint.isallInSetOrConst(this.constantVariables))
                    {
                        continue;
                    }
                    leqDualVariables[i] = this.solver.CreateVariable("dualleq_" + i);

                    var constraintRHS = leqConstraint.getRHS(this.constantVariables);
                    dualObjectiveTerms.Add(leqDualVariables[i]);
                    dualObjectiveCoeff.Add(constraintRHS.Negate());
                }
                Utils.logger("computing dual objective coefficients for equality constraints.", verbose);
                for (int i = 0; i < eqZeroConstraints.Count; i++)
                {
                    var eqConstraint = this.eqZeroConstraints[i];
                    if (eqConstraint.isallInSetOrConst(this.constantVariables))
                    {
                        continue;
                    }
                    eqDualVariables[i] = this.solver.CreateVariable("dualeq_" + i);
                    var constraintRHS = eqConstraint.getRHS(this.constantVariables);
                    dualObjectiveTerms.Add(eqDualVariables[i]);
                    dualObjectiveCoeff.Add(constraintRHS.Negate());
                }
                Utils.logger("ensuring primal objective == dual objective.", verbose);
                // adding primal = dual constraint
                var primalObjective = objective.Negate();
                this.solver.AddEqZeroConstraint(dualObjectiveCoeff, dualObjectiveTerms, primalObjective);
                // adding bound on dual variables
                Utils.logger("ensuring bound on dual variables.", verbose);
                foreach (var (idx, var) in leqDualVariables)
                {
                    // TODO: check this, shouldn't it be >=0?
                    this.solver.AddLeqZeroConstraint(new Polynomial<TVar>(new Term<TVar>(1, var)));
                }
                // adding dual constraints
                Utils.logger("adding dual constraints.", verbose);
                var variableToDualConstraint = new Dictionary<TVar, Polynomial<TVar>>();
                this.distributeComputingDualConstraints(objective, leqDualVariables, eqDualVariables, variableToDualConstraint, verbose);

                Utils.logger(
                    string.Format("Reading the output {0} entries.", variableToDualConstraint.Count),
                    verbose);
                foreach (var (variable, dualConstr) in variableToDualConstraint)
                {
                    if (dualConstr.isallInSetOrConst(new HashSet<TVar>()))
                    {
                        // throw new System.Exception("should not be consant!!!");
                        continue;
                    }
                    this.solver.AddEqZeroConstraint(dualConstr);
                }

                // foreach (var variable in this.Variables) {
                //     if (this.constantVariables.Contains(variable)) {
                //         continue;
                //     }
                //     Polynomial<TVar> dualConstraint = new Polynomial<TVar>();
                //     for (int i = 0; i < leqZeroConstraints.Count; i++) {
                //         var leqConstraint = leqZeroConstraints[i];
                //         var deriv = leqConstraint.Derivative(variable);
                //         if (deriv != 0) {
                //             dualConstraint.Add(new Term<TVar>(deriv, leqDualVariables[i]));
                //         }
                //     }
                //     for (int i = 0; i < eqZeroConstraints.Count; i++) {
                //         var eqConstraint = eqZeroConstraints[i];
                //         var deriv = eqConstraint.Derivative(variable);
                //         if (deriv != 0) {
                //             dualConstraint.Add(new Term<TVar>(deriv, eqDualVariables[i]));
                //         }
                //     }
                //     var objCoeff = objective.Derivative(variable);
                //     dualConstraint.Add(new Term<TVar>(-1 * objCoeff));
                //     this.solver.AddEqZeroConstraint(dualConstraint);
                // }
            }
        }

        // TODO: this function is missing a comment about how it works. Also the varialbe: variableToDualConstraints
        // is not clear in terms of what it does. You need a better name and you need comments to define what each variable does.
        private void distributeComputingDualConstraints(Polynomial<TVar> objective, IDictionary<int, TVar> leqDualVariables,
                IDictionary<int, TVar> eqDualVariables, IDictionary<TVar, Polynomial<TVar>> variableToDualConstraint,
                bool verbose)
        {
            foreach (var variable in this.Variables)
            {
                if (this.constantVariables.Contains(variable))
                {
                    continue;
                }
                var objCoeff = objective.Derivative(variable);
                if (objCoeff == 0)
                {
                    continue;
                }
                variableToDualConstraint[variable] = new Polynomial<TVar>(new Term<TVar>(-1 * objCoeff));
            }

            if (this.NumProcesses <= 1)
            {
                computeDualConstraints(this.leqZeroConstraints, this.eqZeroConstraints, leqDualVariables,
                    eqDualVariables, variableToDualConstraint, verbose: verbose);
                return;
            }
            // TODO: need a comment here.
            var perProcessVariableToDualConstrintMapping = new Dictionary<int, Dictionary<TVar, Polynomial<TVar>>>();
            var perProcessLeqZeroConstraints = new Dictionary<int, List<Polynomial<TVar>>>();
            var perProcessLeqDualVariables = new Dictionary<int, Dictionary<int, TVar>>();
            var perProcessEqZeroConstraints = new Dictionary<int, List<Polynomial<TVar>>>();
            var perProcessEqDualVariables = new Dictionary<int, Dictionary<int, TVar>>();
            int pid = 0;
            for (pid = 0; pid < this.NumProcesses; pid++)
            {
                perProcessVariableToDualConstrintMapping[pid] = new Dictionary<TVar, Polynomial<TVar>>();
                perProcessLeqZeroConstraints[pid] = new List<Polynomial<TVar>>();
                perProcessEqZeroConstraints[pid] = new List<Polynomial<TVar>>();
                perProcessLeqDualVariables[pid] = new Dictionary<int, TVar>();
                perProcessEqDualVariables[pid] = new Dictionary<int, TVar>();
            }
            pid = 0;
            for (int i = 0; i < this.leqZeroConstraints.Count; i++)
            {
                perProcessLeqZeroConstraints[pid].Add(this.leqZeroConstraints[i]);
                perProcessLeqDualVariables[pid][(i - pid) / NumProcesses] = leqDualVariables[i];
                pid = (pid + 1) % NumProcesses;
            }
            pid = 0;
            for (int i = 0; i < this.eqZeroConstraints.Count; i++)
            {
                perProcessEqZeroConstraints[pid].Add(this.eqZeroConstraints[i]);
                perProcessEqDualVariables[pid][(i - pid) / NumProcesses] = eqDualVariables[i];
                pid = (pid + 1) % NumProcesses;
            }

            Utils.logger(
                string.Format("{0} eq constraints and {1} leq constraints in total.", eqZeroConstraints.Count, leqZeroConstraints.Count),
                verbose);
            var threadList = new List<Thread>();
            for (pid = 0; pid < this.NumProcesses; pid++)
            {
                Utils.logger(
                    string.Format("creating process with pid {0}.", pid),
                    verbose);
                threadList.Add(new Thread(() => computeDualConstraints(perProcessLeqZeroConstraints[pid],
                                                                       perProcessEqZeroConstraints[pid],
                                                                       perProcessLeqDualVariables[pid],
                                                                       perProcessEqDualVariables[pid],
                                                                       perProcessVariableToDualConstrintMapping[pid],
                                                                       pid, verbose)));
                Utils.logger(
                    string.Format("starting process with pid {0}.", pid),
                    verbose);
                threadList[pid].Start();
                Thread.Sleep(1000);
            }
            pid = 0;
            foreach (var thread in threadList)
            {
                Utils.logger(
                    string.Format("waiting for process with pid {0}.", pid),
                    verbose);
                thread.Join();
                pid++;
            }
            foreach (var (id, output) in perProcessVariableToDualConstrintMapping)
            {
                Utils.logger(
                    string.Format("Reading the output of pid = {0} with {1} entries.", pid, output.Count),
                    verbose);
                foreach (var (variable, polyTerm) in output)
                {
                    if (!variableToDualConstraint.ContainsKey(variable))
                    {
                        variableToDualConstraint[variable] = new Polynomial<TVar>();
                    }
                    variableToDualConstraint[variable].Add(polyTerm);
                }
            }
        }

        // TODO: needs a comment that describes the input variables and what this function is doing.
        private void computeDualConstraints(IList<Polynomial<TVar>> leqZeroConstraints,
                IList<Polynomial<TVar>> eqZeroConstraints, IDictionary<int, TVar> leqDualVariables,
                IDictionary<int, TVar> eqDualVariables, IDictionary<TVar, Polynomial<TVar>> variableToDualConstraint,
                int pid = -1, bool verbose = false)
        {
            Utils.logger(
                string.Format("pid = {0}: computing dual constraints for {1} leqZero Constraints in primal.", pid, leqZeroConstraints.Count),
                verbose);
            for (int i = 0; i < leqZeroConstraints.Count; i++)
            {
                var leqConstraint = leqZeroConstraints[i];
                foreach (Term<TVar> term in leqConstraint.GetTerms())
                {
                    if (term.isInSetOrConst(this.constantVariables))
                    {
                        continue;
                    }
                    TVar variable = term.Variable.Value;
                    var deriv = leqConstraint.Derivative(variable);
                    if (deriv != 0)
                    {
                        if (!variableToDualConstraint.ContainsKey(variable))
                        {
                            variableToDualConstraint[variable] = new Polynomial<TVar>();
                        }
                        variableToDualConstraint[variable].Add(new Term<TVar>(deriv, leqDualVariables[i]));
                    }
                }
            }

            Utils.logger(
                string.Format("pid = {0}: computing dual constraints for {1} eqZero Constraints in primal.", pid, eqZeroConstraints.Count),
                verbose);
            for (int i = 0; i < eqZeroConstraints.Count; i++)
            {
                var eqConstraint = eqZeroConstraints[i];
                foreach (Term<TVar> term in eqConstraint.GetTerms())
                {
                    if (term.isInSetOrConst(this.constantVariables))
                    {
                        continue;
                    }
                    TVar variable = term.Variable.Value;
                    var deriv = eqConstraint.Derivative(variable);
                    if (deriv != 0)
                    {
                        if (!variableToDualConstraint.ContainsKey(variable))
                        {
                            variableToDualConstraint[variable] = new Polynomial<TVar>();
                        }
                        variableToDualConstraint[variable].Add(new Term<TVar>(deriv, eqDualVariables[i]));
                    }
                }
            }
        }
    }
}