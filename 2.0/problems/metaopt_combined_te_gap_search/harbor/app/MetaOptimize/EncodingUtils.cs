namespace MetaOptimize {
    using System;
    using System.Collections.Generic;
    using Gurobi;
    /// <summary>
    /// Implements a utility function with some .
    /// </summary>
    public static class EncodingUtils<TVar, TSolution> {
        /// <summary>
        /// takes a general continuous and a binary variable.
        /// returns a variable = multiplication of the continuous var and binary or not binary.
        /// </summary>
        public static TVar LinearizeMultGenContinAndBinary(ISolver<TVar, TSolution> solver, TVar contVar,
            TVar binVar, double bigM, bool notBinary = false)
        {
            // aux = contX * y or contX * (1 - y)
            var output = solver.CreateVariable("output_multiplication");
            LinearizeMultGenContinAndBinary(solver, contVar, binVar, output, bigM, notBinary);
            return output;
        }

        /// <summary>
        /// takes a general continuous and a binary variable.
        /// stores in output: multiplication of the continuous var and binary or not binary.
        /// </summary>
        public static void LinearizeMultGenContinAndBinary(ISolver<TVar, TSolution> solver, TVar contVar,
            TVar binVar, TVar output, double bigM, bool notBinary = false)
        {
            // aux = contX * y or contX * (1 - y)
            LinearizeMultGenContinAndBinary(solver,
                new Polynomial<TVar>(new Term<TVar>(1, contVar)),
                binVar, output, bigM, notBinary);
        }

        /// <summary>
        /// takes a general continuous polynomial and a binary variable.
        /// returns a variable = multiplication of the continuous var and binary or not binary.
        /// </summary>
        public static TVar LinearizeMultGenContinAndBinary(ISolver<TVar, TSolution> solver, Polynomial<TVar> contPoly,
            TVar binVar, double bigM, bool notBinary = false)
        {
            // aux = contX * y or contX * (1 - y)
            var output = solver.CreateVariable("output_multiplication");
            LinearizeMultGenContinAndBinary(solver, contPoly, binVar, output, bigM, notBinary);
            return output;
        }

        /// <summary>
        /// takes a general continuous polynomial and a binary variable.
        /// stores in output: multiplication of the continuous var and binary or not binary.
        /// </summary>
        public static void LinearizeMultGenContinAndBinary(ISolver<TVar, TSolution> solver, Polynomial<TVar> contPoly,
            TVar binVar, TVar output, double bigM, bool notBinary = false)
        {
            var const1 = new Polynomial<TVar>(new Term<TVar>(-1, output));
            const1.Add(contPoly);
            if (notBinary) {
                // output >= y_i - M x_i
                const1.Add(new Term<TVar>(-bigM, binVar));
            } else {
                // output >= y_i - M (1 - x_i)
                const1.Add(new Term<TVar>(-bigM));
                const1.Add(new Term<TVar>(bigM, binVar));
            }
            solver.AddLeqZeroConstraint(const1);

            var const2 = new Polynomial<TVar>(new Term<TVar>(-1, output));
            if (notBinary) {
                // output >= - M(1 - x_i)
                const2.Add(new Term<TVar>(-bigM));
                const2.Add(new Term<TVar>(bigM, binVar));
            } else {
                // output >= - Mx_i
                const2.Add(new Term<TVar>(-bigM, binVar));
            }
            solver.AddLeqZeroConstraint(const2);

            var const3 = new Polynomial<TVar>(new Term<TVar>(1, output));
            const3.Add(contPoly.Negate());
            if (notBinary) {
                // output <= y_i + Mx_i
                const3.Add(new Term<TVar>(-bigM, binVar));
            } else {
                // output <= y_i + M(1 - x_i)
                const3.Add(new Term<TVar>(-bigM));
                const3.Add(new Term<TVar>(bigM, binVar));
            }
            solver.AddLeqZeroConstraint(const3);

            var const4 = new Polynomial<TVar>(new Term<TVar>(1, output));
            if (notBinary) {
                // output <= M(1 - x_i)
                const4.Add(new Term<TVar>(-bigM));
                const4.Add(new Term<TVar>(bigM, binVar));
            } else {
                // output <= Mx_i
                const4.Add(new Term<TVar>(-bigM, binVar));
            }
            solver.AddLeqZeroConstraint(const4);
        }

        /// <summary>
        /// takes a non-negative continuous and a binary variable.
        /// returns a variable = multiplication of the continuous var and binary or not binary.
        /// </summary>
        public static TVar LinearizeMultNonNegContinAndBinary(ISolver<TVar, TSolution> solver, TVar contVar,
            TVar binVar, double bigM, bool notBinary = false)
        {
            // aux = contX * y or contX * (1 - y)
            var output = solver.CreateVariable("output_multiplication", lb: 0);
            LinearizeMultNonNegContinAndBinary(solver, contVar, binVar, output, bigM, notBinary);
            return output;
        }

        /// <summary>
        /// takes a non-negative continuous and a binary variable.
        /// stores in output: multiplication of the continuous var and binary or not binary.
        /// </summary>
        public static void LinearizeMultNonNegContinAndBinary(ISolver<TVar, TSolution> solver, TVar contVar,
            TVar binVar, TVar output, double bigM, bool notBinary = false)
        {
            LinearizeMultNonNegContinAndBinary(solver,
                new Polynomial<TVar>(new Term<TVar>(1, contVar)),
                binVar, output, bigM, notBinary);
        }
        /// <summary>
        /// takes a non-negative continuous polynomial and a binary variable.
        /// return a variable = multiplication of the continuous var and binary or not binary.
        /// </summary>
        public static TVar LinearizeMultNonNegContinAndBinary(ISolver<TVar, TSolution> solver, Polynomial<TVar> contPoly,
            TVar binVar, double bigM, bool notBinary = false)
        {
            // output = contX * y or contX * (1 - y)
            var output = solver.CreateVariable("output_multiplication", lb: 0);
            LinearizeMultNonNegContinAndBinary(solver, contPoly, binVar, output, bigM, notBinary);
            return output;
        }

        /// <summary>
        /// takes a non-negative continuous polynomial and a binary variable.
        /// stores in output: multiplication of the continuous var and binary or not binary.
        /// </summary>
        public static void LinearizeMultNonNegContinAndBinary(ISolver<TVar, TSolution> solver, Polynomial<TVar> contPoly,
            TVar binVar, TVar output, double bigM, bool notBinary = false)
        {
            var firstPoly = new Polynomial<TVar>(new Term<TVar>(1, output));
            if (notBinary) {
                // aux <= M * (1 - y)
                firstPoly.Add(new Term<TVar>(-1 * bigM));
                firstPoly.Add(new Term<TVar>(bigM, binVar));
            } else {
                // aux <= M * y
                firstPoly.Add(new Term<TVar>(-1 * bigM, binVar));
            }
            solver.AddLeqZeroConstraint(firstPoly);

            // aux <= contPoly
            var secondPoly = new Polynomial<TVar>(new Term<TVar>(1, output));
            secondPoly.Add(contPoly.Negate());
            solver.AddLeqZeroConstraint(secondPoly);

            var thirdPoly = new Polynomial<TVar>(new Term<TVar>(-1, output));
            thirdPoly.Add(contPoly);
            if (notBinary) {
                // aux >= contPoly - My
                thirdPoly.Add(new Term<TVar>(-1 * bigM, binVar));
            } else {
                // aux >= currW - M (1 - y)
                thirdPoly.Add(new Term<TVar>(bigM, binVar));
                thirdPoly.Add(new Term<TVar>(-1 * bigM));
            }
            solver.AddLeqZeroConstraint(thirdPoly);
        }

        /// <summary>
        /// takes two binary variables.
        /// return a variable = multiplication of a binary var and another binary or not binary.
        /// </summary>
        public static TVar LinearizeMultTwoBinary(ISolver<TVar, TSolution> solver, TVar x, TVar y, bool notY = false)
        {
            // aux = x * y or x * (1 - y)
            var auxOldW = solver.CreateVariable("output_multiplication", type: GRB.BINARY);
            LinearizeMultTwoBinary(solver, x, y, auxOldW, notY);
            return auxOldW;
        }

        /// <summary>
        /// takes two binary variables.
        /// return a variable = multiplication of a binary var and another binary or not binary.
        /// </summary>
        public static void LinearizeMultTwoBinary(ISolver<TVar, TSolution> solver, TVar x, TVar y, TVar output, bool notY = false)
        {
            var firstPoly = new Polynomial<TVar>(new Term<TVar>(1, output));
            if (notY)
            {
                // aux <= 1 - y
                firstPoly.Add(new Term<TVar>(-1));
                firstPoly.Add(new Term<TVar>(1, y));
            } else {
                // aux <= y
                firstPoly.Add(new Term<TVar>(-1, y));
            }
            solver.AddLeqZeroConstraint(firstPoly);

            // aux <= x
            var secondPoly = new Polynomial<TVar>(
                new Term<TVar>(1, output),
                new Term<TVar>(-1, x));
            solver.AddLeqZeroConstraint(secondPoly);

            var thirdPoly = new Polynomial<TVar>(new Term<TVar>(-1, output));
            thirdPoly.Add(new Term<TVar>(1, x));
            if (notY) {
                // aux >= x - y
                thirdPoly.Add(new Term<TVar>(-1, y));
            } else {
                // aux >= x + y - 1
                thirdPoly.Add(new Term<TVar>(1, y));
                thirdPoly.Add(new Term<TVar>(-1));
            }
            solver.AddLeqZeroConstraint(thirdPoly);
        }

        /// <summary>
        /// max two variables.
        /// </summary>
        public static void MaxTwoVar(ISolver<TVar, TSolution> solver, TVar output, TVar x, TVar y, double bigM)
        {
            MaxTwoVar(solver, output,
                new Polynomial<TVar>(new Term<TVar>(1, x)),
                new Polynomial<TVar>(new Term<TVar>(1, y)),
                bigM);
        }

        /// <summary>
        /// max two variables. return the resulting var.
        /// </summary>
        public static TVar MaxTwoVar(ISolver<TVar, TSolution> solver, TVar x, TVar y, double bigM)
        {
            var output = solver.CreateVariable("max_two_aux");
            MaxTwoVar(solver, output, x, y, bigM);
            return output;
        }

        /// <summary>
        /// max of polynomial x and variable y.
        /// </summary>
        public static void MaxTwoVar(ISolver<TVar, TSolution> solver, TVar output, Polynomial<TVar> x, TVar y, double bigM)
        {
            MaxTwoVar(solver, output, x,
                new Polynomial<TVar>(new Term<TVar>(1, y)),
                bigM);
        }

        /// <summary>
        /// max of polynomial x and variable y. returns the resulting variable.
        /// </summary>
        public static TVar MaxTwoVar(ISolver<TVar, TSolution> solver, Polynomial<TVar> x, TVar y, double bigM)
        {
            var output = solver.CreateVariable("max_two_aux");
            MaxTwoVar(solver, output, x, y, bigM);
            return output;
        }

        /// <summary>
        /// max of two polynomial x and y.
        /// </summary>
        public static void MaxTwoVar(ISolver<TVar, TSolution> solver, TVar output, Polynomial<TVar> x, Polynomial<TVar> y, double bigM)
        {
            // z = max(x, y)
            var auxBin = solver.CreateVariable("bin_max", type: GRB.BINARY);
            // z >= x
            var firstPoly = new Polynomial<TVar>(new Term<TVar>(-1, output));
            firstPoly.Add(x);
            solver.AddLeqZeroConstraint(firstPoly);
            // z >= y
            var secondPoly = new Polynomial<TVar>(new Term<TVar>(-1, output));
            secondPoly.Add(y);
            solver.AddLeqZeroConstraint(secondPoly);
            // z <= x + M * b
            var thirdPoly = new Polynomial<TVar>(
                new Term<TVar>(1, output),
                new Term<TVar>(-1 * bigM, auxBin));
            thirdPoly.Add(x.Negate());
            solver.AddLeqZeroConstraint(thirdPoly);
            // z <= y + M * (1 - b)
            var fourthPoly = new Polynomial<TVar>(
                new Term<TVar>(1, output),
                new Term<TVar>(-1 * bigM),
                new Term<TVar>(bigM, auxBin));
            fourthPoly.Add(y.Negate());
            solver.AddLeqZeroConstraint(fourthPoly);
        }

        /// <summary>
        /// max of two polynomial x and y. returns the resulting variable.
        /// </summary>
        public static TVar MaxTwoVar(ISolver<TVar, TSolution> solver, Polynomial<TVar> x, Polynomial<TVar> y, double bigM)
        {
            var output = solver.CreateVariable("max_two_aux");
            MaxTwoVar(solver, output, x, y, bigM);
            return output;
        }

        /// <summary>
        /// min two variables.
        /// </summary>
        public static void MinTwoVar(ISolver<TVar, TSolution> solver, TVar output, TVar x, TVar y, double bigM) {
            // z = min(x, y)
            var auxBin = solver.CreateVariable("bin_max", type: GRB.BINARY);
            // z <= x
            var firstPoly = new Polynomial<TVar>(
                new Term<TVar>(1, output),
                new Term<TVar>(-1, x));
            solver.AddLeqZeroConstraint(firstPoly);
            // z <= y
            var secondPoly = new Polynomial<TVar>(
                new Term<TVar>(1, output),
                new Term<TVar>(-1, y));
            solver.AddLeqZeroConstraint(secondPoly);
            // z >= x - M * b
            var thirdPoly = new Polynomial<TVar>(
                new Term<TVar>(-1, output),
                new Term<TVar>(1, x),
                new Term<TVar>(-1 * bigM, auxBin));
            solver.AddLeqZeroConstraint(thirdPoly);
            // z >= y - M * (1 - b)
            var fourthPoly = new Polynomial<TVar>(
                new Term<TVar>(-1, output),
                new Term<TVar>(1, y),
                new Term<TVar>(-1 * bigM),
                new Term<TVar>(bigM, auxBin));
            solver.AddLeqZeroConstraint(fourthPoly);
        }

        /// <summary>
        /// Or of two binary polynomials.
        /// </summary>
        public static void OrTwoPolyBinary(ISolver<TVar, TSolution> solver, TVar output, TVar a, TVar b)
        {
            var poly1 = new Polynomial<TVar>(new Term<TVar>(1, a));
            var poly2 = new Polynomial<TVar>(new Term<TVar>(1, b));
            OrTwoPolyBinary(solver, output, poly1, poly2);
        }

        /// <summary>
        /// Or of two binary polynomials.
        /// </summary>
        public static void OrTwoPolyBinary(ISolver<TVar, TSolution> solver, TVar output, Polynomial<TVar> polyA, Polynomial<TVar> polyB)
        {
            // z = polyA or polyB
            // z >= polyA
            var poly1 = new Polynomial<TVar>(new Term<TVar>(-1, output));
            poly1.Add(polyA.Copy());
            solver.AddLeqZeroConstraint(poly1);
            // z >= polyB
            var poly2 = new Polynomial<TVar>(new Term<TVar>(-1, output));
            poly2.Add(polyB.Copy());
            solver.AddLeqZeroConstraint(poly2);
            // z <= polyA + polyB
            var poly3 = new Polynomial<TVar>(new Term<TVar>(1, output));
            poly3.Add(polyA.Negate());
            poly3.Add(polyB.Negate());
            solver.AddLeqZeroConstraint(poly3);
        }

        /// <summary>
        /// output = 1 if x \leq y otherwise = 0.
        /// bigM should be > max(|x - y|).
        /// miu should be less than min non zero(|x - y|).
        /// </summary>
        public static TVar IsLeq(ISolver<TVar, TSolution> solver, TVar x, TVar y, double bigM, double miu)
        {
            TVar output = solver.CreateVariable("x_leq_y", GRB.BINARY);
            IsLeq(solver, output, x, y, bigM, miu);
            return output;
        }

        /// <summary>
        /// output = 1 if x \leq y otherwise = 0.
        /// bigM should be > max(|x - y|).
        /// miu should be less than min non zero(|x - y|).
        /// </summary>
        public static TVar IsLeq(ISolver<TVar, TSolution> solver, Polynomial<TVar> x, TVar y, double bigM, double miu)
        {
            TVar output = solver.CreateVariable("x_leq_y", GRB.BINARY);
            IsLeq(solver, output, x,
                  new Polynomial<TVar>(new Term<TVar>(1, y)),
                  bigM, miu);
            return output;
        }

        /// <summary>
        /// output = 1 if x \leq y otherwise = 0.
        /// bigM should be > max(|x - y|).
        /// miu should be less than min non zero(|x - y|).
        /// </summary>
        public static void IsLeq(ISolver<TVar, TSolution> solver, TVar output,
            TVar x, TVar y, double bigM, double miu)
        {
            IsLeq(solver, output,
                new Polynomial<TVar>(new Term<TVar>(1, x)),
                new Polynomial<TVar>(new Term<TVar>(1, y)),
                bigM, miu);
        }

        /// <summary>
        /// output = 1 if x \leq y otherwise = 0.
        /// bigM should be > max(|x - y|).
        /// miu should be less than min non zero(|x - y|).
        /// </summary>
        public static TVar IsLeq(ISolver<TVar, TSolution> solver,
            TVar x, Polynomial<TVar> y, double bigM, double miu)
        {
            TVar output = solver.CreateVariable("x_leq_y", GRB.BINARY);
            IsLeq(solver, output,
                new Polynomial<TVar>(new Term<TVar>(1, x)),
                y, bigM, miu);
            return output;
        }
        /// <summary>
        /// output = 1 if x \leq y otherwise = 0.
        /// bigM should be > max(|x - y|).
        /// miu should be less than min non zero(|x - y|).
        /// </summary>
        public static TVar IsLeq(ISolver<TVar, TSolution> solver,
            Polynomial<TVar> x, Polynomial<TVar> y, double bigM, double miu)
        {
            TVar output = solver.CreateVariable("x_leq_y", GRB.BINARY);
            IsLeq(solver, output, x, y, bigM, miu);
            return output;
        }
        /// <summary>
        /// output = 1 if x \leq y otherwise = 0.
        /// bigM should be > max(|x - y|).
        /// miu should be less than min non zero(|x - y|).
        /// </summary>
        public static void IsLeq(ISolver<TVar, TSolution> solver, TVar output,
            Polynomial<TVar> x, Polynomial<TVar> y, double bigM, double miu)
        {
            double epsilon = 1.0 / bigM;
            // z <= 1 + epsilon * (y - x)
            var constr1 = new Polynomial<TVar>(
                new Term<TVar>(1, output),
                new Term<TVar>(-1));
            constr1.Add(x.Multiply(epsilon));
            constr1.Add(y.Multiply(-epsilon));
            solver.AddLeqZeroConstraint(constr1);

            // z >= epsilon * (y - x + miu)
            var constr2 = new Polynomial<TVar>(
                new Term<TVar>(-1, output),
                new Term<TVar>(miu * epsilon));
            constr2.Add(x.Multiply(-epsilon));
            constr2.Add(y.Multiply(epsilon));
            solver.AddLeqZeroConstraint(constr2);
        }

        /// <summary>
        /// output = 1 if x less than y otherwise = 0.
        /// bigM should be > max(|x - y|).
        /// miu should be less than min non zero(|x - y|).
        /// </summary>
        public static TVar IsLess(ISolver<TVar, TSolution> solver,
            TVar x, TVar y, double bigM, double miu)
        {
            TVar output = solver.CreateVariable("x_less_y", GRB.BINARY);
            IsLess(solver, output, x, y, bigM, miu);
            return output;
        }

        /// <summary>
        /// output = 1 if x less than y otherwise = 0.
        /// bigM should be > max(|x - y|).
        /// miu should be less than min non zero(|x - y|).
        /// </summary>
        public static void IsLess(ISolver<TVar, TSolution> solver, TVar output,
            TVar x, TVar y, double bigM, double miu)
        {
            double epsilon = 1.0 / bigM;
            // z <= 1 + epsilon * (y - x - miu)
            var constr1 = new Polynomial<TVar>(
                new Term<TVar>(1, output),
                new Term<TVar>(-1 + epsilon * miu),
                new Term<TVar>(-epsilon, y),
                new Term<TVar>(epsilon, x));
            solver.AddLeqZeroConstraint(constr1);

            // z >= epsilon * (y - x)
            var constr2 = new Polynomial<TVar>(
                new Term<TVar>(-1, output),
                new Term<TVar>(epsilon, y),
                new Term<TVar>(-epsilon, x));
            solver.AddLeqZeroConstraint(constr2);
        }

        /// <summary>
        /// Estimate the relative rank of a variable with respect to a list of variables.
        /// bigM should be > max(|varList[i] - x|).
        /// miu should be less than min non zero(|varList[i] - x|).
        /// </summary>
        public static TVar ComputeQuantile(ISolver<TVar, TSolution> solver, TVar x,
            IList<TVar> varList, double bigM, double miu)
        {
            // output = (number of elements less than or equal to output) / num elements
            TVar output = solver.CreateVariable("quantile");
            var constr1 = new Polynomial<TVar>(new Term<TVar>(-varList.Count, output));
            foreach (TVar var in varList) {
                constr1.Add(new Term<TVar>(1, IsLess(solver, var, x, bigM, miu)));
            }
            solver.AddEqZeroConstraint(constr1);
            return output;
        }

        /// <summary>
        /// output should be less than or equal to 0 if x > y.
        /// bigM should be > max(|x - y|).
        /// </summary>
        public static void UpperBoundByZeroIfGreater(ISolver<TVar, TSolution> solver,
            Polynomial<TVar> BinaryOutput, Polynomial<TVar> x, double y, double bigM)
        {
            var polyY = new Polynomial<TVar>(new Term<TVar>(y));
            UpperBoundByZeroIfGreater(solver, BinaryOutput, x, polyY, bigM);
        }
        /// <summary>
        /// output should be less than or equal to 0 if x > y.
        /// bigM should be > max(|x - y|).
        /// </summary>
        public static void UpperBoundByZeroIfGreater(ISolver<TVar, TSolution> solver,
            Polynomial<TVar> BinaryOutput, Polynomial<TVar> x, Polynomial<TVar> y, double bigM)
        {
            double epsilon = 1.0 / bigM;
            // z <= 1 + epsilon * (y - x)
            var constr1 = new Polynomial<TVar>(new Term<TVar>(-1));
            constr1.Add(BinaryOutput);
            constr1.Add(x.Multiply(epsilon));
            constr1.Add(y.Multiply(-epsilon));
            solver.AddLeqZeroConstraint(constr1);
        }

        /// <summary>
        /// output should be less than or equal to 0 if x \geq y.
        /// bigM should be > max(|x - y|).
        /// miu should be less than min non zero(|x - y|).
        /// </summary>
        public static void UpperBoundByZeroIfGeq(ISolver<TVar, TSolution> solver,
            Polynomial<TVar> BinaryOutput, double x, Polynomial<TVar> y, double bigM, double miu)
        {
            var polyX = new Polynomial<TVar>(new Term<TVar>(x));
            UpperBoundByZeroIfGeq(solver, BinaryOutput, polyX, y, bigM, miu);
        }
        /// <summary>
        /// output should be less than or equal to 0 if x \geq y.
        /// bigM should be > max(|x - y|).
        /// miu should be less than min non zero(|x - y|).
        /// </summary>
        public static void UpperBoundByZeroIfGeq(ISolver<TVar, TSolution> solver,
            Polynomial<TVar> BinaryOutput, Polynomial<TVar> x, Polynomial<TVar> y, double bigM, double miu)
        {
            double epsilon = 1.0 / bigM;
            // z <= 1 + epsilon * (y - x - miu)
            var constr1 = new Polynomial<TVar>(new Term<TVar>(-1 + epsilon * miu));
            constr1.Add(BinaryOutput);
            constr1.Add(x.Multiply(epsilon));
            constr1.Add(y.Multiply(-epsilon));
            solver.AddLeqZeroConstraint(constr1);
        }
    }
}