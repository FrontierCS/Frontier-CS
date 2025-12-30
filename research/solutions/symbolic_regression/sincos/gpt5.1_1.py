import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        if X.ndim != 2 or X.shape[1] != 2:
            raise ValueError("X must have shape (n, 2)")

        n_samples = X.shape[0]
        if n_samples == 0:
            return {
                "expression": "0",
                "predictions": [],
                "details": {}
            }

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Build feature matrix
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)
        s_sum = np.sin(x1 + x2)
        c_sum = np.cos(x1 + x2)
        s_diff = np.sin(x1 - x2)
        c_diff = np.cos(x1 - x2)
        ones = np.ones_like(x1)

        A = np.column_stack([
            s1,      # 0: sin(x1)
            c1,      # 1: cos(x1)
            s2,      # 2: sin(x2)
            c2,      # 3: cos(x2)
            s_sum,   # 4: sin(x1 + x2)
            c_sum,   # 5: cos(x1 + x2)
            s_diff,  # 6: sin(x1 - x2)
            c_diff,  # 7: cos(x1 - x2)
            ones     # 8: constant
        ])

        # Least-squares fit
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        y_pred = A @ coeffs

        # Map features to expression strings
        term_exprs = [
            "sin(x1)",          # 0
            "cos(x1)",          # 1
            "sin(x2)",          # 2
            "cos(x2)",          # 3
            "sin(x1 + x2)",     # 4
            "cos(x1 + x2)",     # 5
            "sin(x1 - x2)",     # 6
            "cos(x1 - x2)",     # 7
            "1"                 # 8: constant
        ]

        def format_coefficient(c: float) -> str:
            if abs(c) < 1e-15:
                return "0"
            s = f"{c:.12g}"
            if s == "-0":
                s = "0"
            return s

        max_abs_coeff = float(np.max(np.abs(coeffs))) if coeffs.size > 0 else 0.0
        threshold = 1e-5 * (1.0 + max_abs_coeff)

        nonconst_terms = []
        const_value = 0.0

        for coef, expr in zip(coeffs, term_exprs):
            if abs(coef) < threshold:
                continue
            if expr == "1":
                const_value += coef
            else:
                c = coef
                # Simplify coefficients close to 1 or -1
                if abs(c - 1.0) < 1e-8:
                    term_str = expr
                elif abs(c + 1.0) < 1e-8:
                    term_str = f"-({expr})"
                else:
                    coef_str = format_coefficient(c)
                    term_str = f"{coef_str}*({expr})"
                nonconst_terms.append(term_str)

        terms_str = list(nonconst_terms)

        if abs(const_value) >= threshold or (not terms_str and const_value != 0.0):
            const_str = format_coefficient(const_value)
            terms_str.append(const_str)

        if not terms_str:
            expression = "0"
        else:
            expression = " + ".join(terms_str)

        return {
            "expression": expression,
            "predictions": y_pred.tolist(),
            "details": {}
        }