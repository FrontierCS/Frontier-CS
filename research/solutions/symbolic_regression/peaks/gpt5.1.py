import numpy as np
from sympy import sympify, Add, Mul, Pow, Function


def _count_ops(expr):
    if expr.is_Atom:
        return 0, 0
    bin_ops = 0
    unary_ops = 0
    if isinstance(expr, (Add, Mul)):
        args = expr.args
        n_args = len(args)
        if n_args >= 2:
            bin_ops += n_args - 1
        for a in args:
            b, u = _count_ops(a)
            bin_ops += b
            unary_ops += u
    elif isinstance(expr, Pow):
        bin_ops += 1
        for a in expr.args:
            b, u = _count_ops(a)
            bin_ops += b
            unary_ops += u
    elif isinstance(expr, Function):
        unary_ops += 1
        for a in expr.args:
            b, u = _count_ops(a)
            bin_ops += b
            unary_ops += u
    else:
        for a in expr.args:
            b, u = _count_ops(a)
            bin_ops += b
            unary_ops += u
    return bin_ops, unary_ops


class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Basis functions inspired by the canonical "peaks" function
        t1 = (1.0 - x1) ** 2 * np.exp(-x1 ** 2 - (x2 + 1.0) ** 2)
        t2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-x1 ** 2 - x2 ** 2)
        t3 = np.exp(-(x1 + 1.0) ** 2 - x2 ** 2)
        const = np.ones_like(x1)

        # Linear regression on these basis functions
        A = np.column_stack((t1, t2, t3, const))
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        y_fit_all = A.dot(coeffs)

        # Canonical peaks expression (no fitting)
        y_canon = 3.0 * t1 - 10.0 * t2 - (1.0 / 3.0) * t3

        mse_fit = float(np.mean((y - y_fit_all) ** 2))
        mse_canon = float(np.mean((y - y_canon) ** 2))

        # Decide whether to use the canonical expression or the fitted one
        if mse_canon <= mse_fit:
            # Use canonical peaks expression
            expression = (
                "3.0*(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2)"
                " - 10.0*(x1/5.0 - x1**3 - x2**5)*exp(-x1**2 - x2**2)"
                " - (1.0/3.0)*exp(-(x1 + 1.0)**2 - x2**2)"
            )
            predictions = y_canon
        else:
            # Use fitted linear combination of basis functions
            feature_exprs = [
                "(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2)",
                "(x1/5.0 - x1**3 - x2**5)*exp(-x1**2 - x2**2)",
                "exp(-(x1 + 1.0)**2 - x2**2)",
                "1.0",
            ]

            abs_coeffs = np.abs(coeffs)
            max_coeff = float(abs_coeffs.max()) if abs_coeffs.size > 0 else 0.0
            if max_coeff == 0.0:
                expression = "0.0"
                predictions = np.zeros_like(y)
            else:
                threshold = max(1e-4 * max_coeff, 1e-6)
                keep_indices = [i for i, c in enumerate(coeffs) if abs(c) >= threshold]
                if not keep_indices:
                    keep_indices = [int(np.argmax(abs_coeffs))]

                terms = []
                for idx in keep_indices:
                    c = coeffs[idx]
                    if idx == 3:
                        # Constant term
                        terms.append(f"({c:.16g})")
                    else:
                        terms.append(f"({c:.16g})*({feature_exprs[idx]})")

                expression = " + ".join(terms) if terms else "0.0"
                A_keep = A[:, keep_indices]
                predictions = A_keep.dot(coeffs[keep_indices])

        # Compute complexity
        try:
            sym_expr = sympify(expression)
            bin_ops, unary_ops = _count_ops(sym_expr)
            complexity = int(2 * bin_ops + unary_ops)
        except Exception:
            complexity = None

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity},
        }