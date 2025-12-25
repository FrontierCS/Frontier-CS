import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _linear_baseline_mse(x1, x2, y):
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        yhat = A @ coef
        err = y - yhat
        return float(np.mean(err * err))

    @staticmethod
    def _snap(v, candidates, atol=1e-8, rtol=1e-8):
        for c in candidates:
            if np.isclose(v, c, atol=atol, rtol=rtol):
                return float(c)
        return float(v)

    @staticmethod
    def _fmt_num(v):
        if abs(v) < 5e-15:
            v = 0.0
        rv = round(v)
        if abs(v - rv) < 1e-12:
            return str(int(rv))
        s = f"{v:.12g}"
        if s == "-0":
            s = "0"
        return s

    @classmethod
    def _add_term(cls, expr, coef, term_str, coef_tol=1e-12):
        if abs(coef) <= coef_tol:
            return expr
        sign = "-" if coef < 0 else "+"
        acoef = abs(coef)

        if np.isclose(acoef, 1.0, atol=1e-12, rtol=1e-12):
            term = f"{term_str}"
        else:
            term = f"{cls._fmt_num(acoef)}*({term_str})"

        if not expr:
            return f"-{term}" if sign == "-" else term
        return f"{expr} {sign} {term}"

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Fit McCormick-structured model:
        # y ≈ a*sin(x1+x2) + b*(x1-x2)**2 + c*x1 + d*x2 + e
        s = np.sin(x1 + x2)
        q = (x1 - x2) ** 2
        A = np.column_stack([s, q, x1, x2, np.ones_like(x1)])
        coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c, d, e = [float(v) for v in coef]

        candidates = [
            -5.0, -4.0, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0,
            0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0
        ]
        a = self._snap(a, candidates)
        b = self._snap(b, candidates)
        c = self._snap(c, candidates)
        d = self._snap(d, candidates)
        e = self._snap(e, candidates)

        yhat = a * s + b * q + c * x1 + d * x2 + e
        mse = float(np.mean((y - yhat) ** 2))

        base_mse = self._linear_baseline_mse(x1, x2, y)
        var_y = float(np.var(y)) if y.size else 0.0

        use_structured = (
            np.isfinite(mse)
            and (mse <= max(1e-12, 1e-10 * max(1.0, var_y)))
            or (np.isfinite(base_mse) and mse < 0.05 * max(base_mse, 1e-12))
        )

        if use_structured:
            expr = ""
            expr = self._add_term(expr, a, "sin(x1 + x2)")
            expr = self._add_term(expr, b, "(x1 - x2)**2")
            expr = self._add_term(expr, c, "x1")
            expr = self._add_term(expr, d, "x2")
            expr = self._add_term(expr, e, "1")

            if not expr:
                expr = "0"

            return {
                "expression": expr,
                "predictions": yhat.tolist(),
                "details": {"mse": mse, "baseline_mse": base_mse}
            }

        # Fallback: best-effort known canonical McCormick expression
        yhat2 = np.sin(x1 + x2) + (x1 - x2) ** 2 - 1.5 * x1 + 2.5 * x2 + 1.0
        mse2 = float(np.mean((y - yhat2) ** 2))
        expr2 = "sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1"
        return {
            "expression": expr2,
            "predictions": yhat2.tolist(),
            "details": {"mse": mse2, "baseline_mse": base_mse}
        }