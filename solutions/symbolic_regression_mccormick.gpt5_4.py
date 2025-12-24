import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.relative_tolerance_canonical = kwargs.get("relative_tolerance_canonical", 0.02)
        self.zero_tol = kwargs.get("zero_tol", 1e-12)

    def _fmt_float(self, x: float) -> str:
        if abs(x) < self.zero_tol:
            return "0"
        s = f"{x:.12g}"
        return s

    def _build_expression(self, coefs):
        a, b, c, d, e = coefs
        expr = None

        def add_term(expr, coef, var_expr):
            if abs(coef) <= self.zero_tol:
                return expr
            sign_neg = coef < 0
            abscoef = -coef if sign_neg else coef
            if abs(abscoef - 1.0) <= 1e-12:
                term = var_expr
            else:
                term = f"{self._fmt_float(abscoef)}*{var_expr}"
            if expr is None:
                return (f"- {term}" if sign_neg else term)
            else:
                return expr + (" - " if sign_neg else " + ") + term

        # Terms in canonical order
        expr = add_term(expr, a, "sin(x1 + x2)")
        expr = add_term(expr, b, "(x1 - x2)**2")
        expr = add_term(expr, c, "x1")
        expr = add_term(expr, d, "x2")

        # Constant term
        if abs(e) > self.zero_tol:
            if expr is None:
                expr = self._fmt_float(e)
            else:
                expr = expr + (" - " if e < 0 else " + ") + self._fmt_float(abs(e))

        # Fallback to 0 if all terms stripped
        if expr is None or len(expr.strip()) == 0:
            expr = "0"
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).ravel()

        if X.shape[1] != 2:
            raise ValueError("X must have exactly 2 columns (x1, x2).")

        x1 = X[:, 0]
        x2 = X[:, 1]

        sin12 = np.sin(x1 + x2)
        d = x1 - x2
        d2 = d * d
        ones = np.ones_like(x1)

        # Feature matrix for the canonical McCormick structure
        A = np.column_stack([sin12, d2, x1, x2, ones])

        # Least squares fit
        coefs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        y_pred = A @ coefs
        mse_ls = np.mean((y - y_pred) ** 2)

        # Try canonical exact coefficients of McCormick if they fit well
        coefs_canonical = np.array([1.0, 1.0, -1.5, 2.5, 1.0], dtype=np.float64)
        y_can = A @ coefs_canonical
        mse_can = np.mean((y - y_can) ** 2)

        # Adopt canonical if not worse than a small relative tolerance of the LS solution
        if mse_can <= mse_ls * (1.0 + self.relative_tolerance_canonical) + 1e-12:
            expression = "sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1"
            return {
                "expression": expression,
                "predictions": None,
                "details": {}
            }

        # Otherwise, use fitted coefficients
        expression = self._build_expression(coefs)

        return {
            "expression": expression,
            "predictions": None,
            "details": {}
        }
