// <copyright file="Polynomial.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.Diagnostics;
    using System.Linq;
    using ZenLib;

    /// <summary>
    /// A polynomial such as 3x + 2y + 1.
    /// </summary>
    public class Polynomial<TVar>
    {
        /// <summary>
        /// The polynomial terms.
        /// </summary>
        protected List<Term<TVar>> Terms { get; set; }

        /// <summary>
        /// variable to derivative mapping.
        /// </summary>
        private Dictionary<TVar, double> variableToDerivativeMapping = new Dictionary<TVar, double>();

        private void addNewTermsToDerivativeDict(List<Term<TVar>> polynomialTerms)
        {
            foreach (var term in polynomialTerms)
            {
                addNewTermsToDerivativeDict(term);
            }
        }

        private void addNewTermsToDerivativeDict(Term<TVar> term)
        {
            if (term.isConstant())
            {
                return;
            }
            if (!variableToDerivativeMapping.ContainsKey(term.Variable.Value))
            {
                variableToDerivativeMapping[term.Variable.Value] = 0;
            }
            Debug.Assert(term.Exponent <= 1);
            variableToDerivativeMapping[term.Variable.Value] += term.Coefficient;
        }

        /// <summary>
        /// Creates a new instance of the <see cref="Polynomial{TVar}"/> class.
        /// </summary>
        public Polynomial()
        {
            this.Terms = new List<Term<TVar>>();
        }

        /// <summary>
        /// Creates a new instance of the <see cref="Polynomial{TVar}"/> class.
        /// </summary>
        /// <param name="polynomialTerms">The terms.</param>
        public Polynomial(List<Term<TVar>> polynomialTerms)
        {
            Terms = polynomialTerms;
            addNewTermsToDerivativeDict(polynomialTerms);
        }

        /// <summary>
        /// Creates a new instance of the <see cref="Polynomial{TVar}"/> class.
        /// </summary>
        /// <param name="polynomialTerms">The terms.</param>
        public Polynomial(params Term<TVar>[] polynomialTerms)
        {
            Terms = new List<Term<TVar>>(polynomialTerms);
            addNewTermsToDerivativeDict(new List<Term<TVar>>(polynomialTerms));
        }

        /// <summary>
        /// Convert this polynomial to a Zen form.
        /// </summary>
        /// <returns>A real Zen expression.</returns>
        public Zen<Real> AsZen()
        {
            var p = Zen.Constant(new Real(0));
            foreach (var term in this.Terms)
            {
                p = p + term.AsZen();
            }

            return p;
        }

        /// <summary>
        /// Compute the partial derivative of this polynomial with respect a variable.
        /// </summary>
        /// <param name="variable">The variable.</param>
        /// <returns>The result as a polynomial.</returns>
        public double Derivative(TVar variable)
        {
            if (this.variableToDerivativeMapping.ContainsKey(variable))
            {
                return this.variableToDerivativeMapping[variable];
            }
            else
            {
                return 0;
            }
            // return this.Terms.Select(x => x.Derivative(variable)).Aggregate((a, b) => a + b);
        }

        /// <summary>
        /// add a new term.
        /// </summary>
        /// <param name="newTerm">a new Term.</param>
        public void Add(Term<TVar> newTerm)
        {
            this.Terms.Add(newTerm);
            addNewTermsToDerivativeDict(newTerm);
        }

        /// <summary>
        /// add a new term.
        /// </summary>
        /// <param name="newPolynomial">a new Polynomial.</param>
        public void Add(Polynomial<TVar> newPolynomial)
        {
            foreach (var newTerm in newPolynomial.Terms)
            {
                this.Add(newTerm);
                addNewTermsToDerivativeDict(newTerm);
            }
        }

        /// <summary>
        /// Negate the polynomial.
        /// </summary>
        /// <returns>The result as a polynomial.</returns>
        public Polynomial<TVar> Negate()
        {
            return new Polynomial<TVar>(this.Terms.Select(x => x.Negate()).ToList());
        }

        /// <summary>
        /// copy the polynomial.
        /// </summary>
        /// <returns>The result as a polynomial.</returns>
        public Polynomial<TVar> Copy()
        {
            return new Polynomial<TVar>(this.Terms.Select(x => x.Copy()).ToList());
        }

        /// <summary>
        /// multiply the polynomial by a constant.
        /// </summary>
        /// <returns>The result as a polynomial.</returns>
        public Polynomial<TVar> Multiply(double constant)
        {
            return new Polynomial<TVar>(this.Terms.Select(x => x.Multiply(constant)).ToList());
        }

        /// <summary>
        /// Convert the polynomial to a string.
        /// </summary>
        /// <returns>The string representation.</returns>
        public override string ToString()
        {
            return string.Join(" + ", this.Terms.Select(x => x.ToString()));
        }
        /// <summary>
        /// Checks if all terms in
        /// this linear polynomial
        /// are in variabls.
        /// </summary>
        /// <param name="variables"></param>
        /// <returns></returns>
        public bool isallInSetOrConst(ISet<TVar> variables)
        {
            // how many terms are not in the set and not const.
            var count = this.Terms.Where(x => !x.isInSetOrConst(variables)).Count();
            if (count == 0)
            {
                return true;
            }
            return false;
        }
        /// <summary>
        /// returns the constant of the polynomial.
        /// </summary>
        /// TODO: maybe we should change the name of this function? since
        /// it is based on the assumption that your going to always have the constants on the right hand side
        /// of the constraints, but you dont have to? maybe you should call it getConstants? or something?
        public Polynomial<TVar> getRHS(ISet<TVar> constVariables)
        {
            Polynomial<TVar> rhs = new Polynomial<TVar>();
            foreach (var term in this.Terms)
            {
                if (term.isInSetOrConst(constVariables))
                {
                    rhs.Add(term);
                }
            }
            return rhs;
        }
        /// <summary>
        /// returns if the polynomial containts single variable.
        /// </summary>
        public bool isSingleVariable()
        {
            ISet<Option<TVar>> vars = new HashSet<Option<TVar>>();
            foreach (var term in this.Terms)
            {
                if (term.isConstant())
                {
                    continue;
                }
                vars.Add(term.Variable);
            }
            return (vars.Count() == 1);
        }

        /// <summary>
        /// Returns Readonly version of terms.
        /// </summary>
        public ReadOnlyCollection<Term<TVar>> GetTerms()
        {
            return Terms.AsReadOnly();
        }
        // /// <summary>
        // /// Returns True if the input polynomial is equal to the current one.
        // /// </summary>
        // public bool Equals(Polynomial<TVar> poly) {
        //     foreach (var term1 in poly.Terms) {
        //         bool found = false;
        //         foreach (var term2 in poly.Terms) {
        //             if (term1.Equals(term2)) {
        //                 found = true;
        //             }
        //         }
        //         if (!found) {
        //             return false;
        //         }
        //     }
        //     return true;
        // }

        /// <summary>
        /// get all the terms with coefficient less than or equal to a threshold.
        /// </summary>
        public Polynomial<TVar> GetTermsWithCoeffLeq(double threshold)
        {
            var newTerm = new Polynomial<TVar>();
            foreach (var term in this.Terms)
            {
                if (term.Coefficient <= threshold + 0.00001)
                {
                    newTerm.Add(term.Copy());
                }
            }
            return newTerm;
        }

        /// <summary>
        /// get all the terms with coefficient less than or equal to a threshold.
        /// </summary>
        public Polynomial<TVar> GetTermsWithCoeffGreater(double threshold)
        {
            var newTerm = new Polynomial<TVar>();
            foreach (var term in this.Terms)
            {
                if (term.Coefficient > threshold + 0.00001)
                {
                    newTerm.Add(term.Copy());
                }
            }
            return newTerm;
        }
    }
}
