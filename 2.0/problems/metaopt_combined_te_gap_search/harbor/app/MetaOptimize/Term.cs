// <copyright file="PolynomialTerm.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>
using System.Collections.Generic;

namespace MetaOptimize
{
    using ZenLib;

    /// <summary>
    /// A polynomial term.
    /// </summary>
    public class Term<TVar>
    {
        private int precision = 100;
        /// <summary>
        /// The variable name.
        /// </summary>
        public Option<TVar> Variable { get; set; }

        /// <summary>
        /// The coefficient for the term.
        /// </summary>
        public double Coefficient { get; set; }

        /// <summary>
        /// The exponent for the term.
        /// </summary>
        public byte Exponent { get; set; }

        /// <summary>
        /// Creates a new instance of the <see cref="Term{TVar}"/> class.
        /// </summary>
        /// <param name="coefficient">The constant coefficient.</param>
        public Term(double coefficient)
        {
            this.Coefficient = coefficient;
            this.Exponent = 0;
            this.Variable = Option.None<TVar>();
        }

        /// <summary>
        /// Creates a new instance of the <see cref="Term{TVar}"/> class.
        /// </summary>
        /// <param name="coefficient">The constant coefficient.</param>
        /// <param name="variable">The variable name.</param>
        public Term(double coefficient, TVar variable)
        {
            this.Coefficient = coefficient;
            this.Variable = Option.Some(variable);
            this.Exponent = 1;
        }

        /// <summary>
        /// Creates a new instance of the <see cref="Term{TVar}"/> class.
        /// </summary>
        /// <param name="coefficient">The constant coefficient.</param>
        /// <param name="variable">The variable name.</param>
        /// <param name="exponent">The exponent.</param>
        public Term(double coefficient, TVar variable, byte exponent)
        {
            this.Coefficient = coefficient;
            this.Variable = Option.Some(variable);
            this.Exponent = exponent;
        }

        /// TODO: should this move to the zenSolver library?
        /// <summary>
        /// Convert this polynomial term to a Zen form.
        /// </summary>
        /// <returns>A real Zen expression.</returns>
        public Zen<Real> AsZen()
        {
            if (this.Exponent == 0)
            {
                if ((int)this.Coefficient == Coefficient)
                {
                    return new Real((int)this.Coefficient);
                }
                return new Real((int)(this.Coefficient * precision), precision);
            }

            if (this.Exponent == 1)
            {
                if ((int)this.Coefficient == Coefficient)
                {
                    return new Real((int)this.Coefficient) * (dynamic)this.Variable.Value;
                }
                return new Real((int)(this.Coefficient * precision), precision) * (dynamic)this.Variable.Value;
            }

            throw new System.Exception($"exponent can only be 0 or 1.");
        }

        /// <summary>
        /// Compute the partial derivative of this polynomial term with respect a variable.
        /// </summary>
        /// <param name="variable">The variable.</param>
        /// <returns>The result as a polynomial.</returns>
        /// TODO: function name should change to derivative of linear polynomial or something.
        public double Derivative(TVar variable)
        {
            if (this.Exponent == 0 || !this.Variable.HasValue || !this.Variable.Value.Equals(variable))
            {
                return 0;
            }
            else
            {
                return this.Coefficient;
            }
        }
        /// <summary>
        /// Function that checks if this variable is in a set.
        /// </summary>
        /// <param name="vars">set of variables.</param>
        /// <returns></returns>
        public bool isInSetOrConst(ISet<TVar> vars)
        {
            if (this.Exponent == 0 || !this.Variable.HasValue)
            {
                return true;
            }
            if (!vars.Contains((dynamic)this.Variable.Value))
            {
                return false;
            }
            return true;
        }
        /// <summary>
        /// Function that checks if this variable is a constant.
        /// </summary>
        public bool isConstant()
        {
            if (this.Exponent == 0 || !this.Variable.HasValue)
            {
                return true;
            }
            return false;
        }
        /// <summary>
        /// Negate this polynomial term.
        /// </summary>
        /// <returns></returns>
        public Term<TVar> Negate()
        {
            if (this.Variable.HasValue)
            {
                return new Term<TVar>(-1 * this.Coefficient, this.Variable.Value, this.Exponent);
            }
            else
            {
                return new Term<TVar>(-1 * this.Coefficient);
            }
        }
        /// <summary>
        /// Multiply this polynomial term by a number.
        /// </summary>
        /// <returns></returns>
        /// TODO: do we need to also add instances to multiply variable by variable?
        public Term<TVar> Multiply(double constant)
        {
            if (this.Variable.HasValue)
            {
                return new Term<TVar>(constant * this.Coefficient, this.Variable.Value, this.Exponent);
            }
            else
            {
                return new Term<TVar>(constant * this.Coefficient);
            }
        }
        /// <summary>
        /// Copy this polynomial term.
        /// </summary>
        /// <returns></returns>
        public Term<TVar> Copy()
        {
            if (this.Variable.HasValue)
            {
                return new Term<TVar>(this.Coefficient, this.Variable.Value, this.Exponent);
            }
            else
            {
                return new Term<TVar>(this.Coefficient);
            }
        }

        /// <summary>
        /// Convert this term to a string.
        /// </summary>
        /// <returns>The string representation.</returns>
        public override string ToString()
        {
            if (this.Exponent == 0)
            {
                return this.Coefficient.ToString();
            }
            else
            {
                var prefix = this.Coefficient == 1 ? string.Empty : (this.Coefficient == -1 ? "-" : this.Coefficient.ToString() + "*");
                return $"{prefix}{this.Variable}";
            }
        }
    }
}
