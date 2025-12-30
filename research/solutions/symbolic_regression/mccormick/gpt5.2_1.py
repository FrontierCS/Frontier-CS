import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def _snap_value(self, v: float, tol: float = 1e-6) -> float:
        if not np.isfinite(v):
            return 0.0
        if abs(v) <= 1e-12:
            return 0.0
        snap_vals = np.array([
            -10.0, -8.0, -6.0, -5.0, -4.0, -3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, -0.25,
            0.0,
            0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0
        ], dtype=float)
        idx = int(np.argmin(np.abs(snap_vals - v)))
        sv = float(snap_vals[idx])
        if abs(v - sv) <= tol * max(1.0, abs(v)):
            return sv
        return float(v)

    def _num_to_str(self, v: float) -> str:
        if abs(v - round(v)) <= 1e-12:
            return str(int(round(v)))
        s = format(float(v), ".12g")
        if "e" in s or "E" in s:
            s = format(float(v), ".12f").rstrip("0").rstrip(".")
            if s == "-0":
                s = "0"
        return s

    def _add_term(self, parts, coef: float, term_expr: str, allow_omit_one: bool = True):
        if coef == 0.0:
            return
        sign = 1
        c = float(coef)
        if c < 0:
            sign = -1
            c = -c

        if allow_omit_one and abs(c - 1.0) <= 1e-15:
            expr = term_expr
        else:
            cstr = self._num_to_str(c)
            if term_expr in ("x1", "x2"):
                expr = f"{cstr}*{term_expr}"
            else:
                expr = f"{cstr}*({term_expr})"
        parts.append((sign, expr))

    def _build_expression(self, coeffs: np.ndarray) -> str:
        a, b, c, d, e = [float(v) for v in coeffs]
        parts = []

        self._add_term(parts, a, "sin(x1 + x2)", allow_omit_one=True)
        self._add_term(parts, b, "(x1 - x2)**2", allow_omit_one=True)
        self._add_term(parts, c, "x1", allow_omit_one=True)
        self._add_term(parts, d, "x2", allow_omit_one=True)

        if e != 0.0:
            sign = 1
            v = e
            if v < 0:
                sign = -1
                v = -v
            parts.append((sign, self._num_to_str(v)))

        if not parts:
            return "0"

        expr = parts[0][1] if parts[0][0] > 0 else f"-({parts[0][1]})"
        for sgn, p in parts[1:]:
            if sgn > 0:
                expr = f"{expr} + {p}"
            else:
                expr = f"{expr} - {p}"
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        x1 = X[:, 0].astype(float, copy=False)
        x2 = X[:, 1].astype(float, copy=False)

        t0 = np.sin(x1 + x2)
        t1 = (x1 - x2) ** 2
        A = np.column_stack([t0, t1, x1, x2, np.ones_like(x1)])

        coeffs, _, _, _ = np.linalg.lstsq(A, y.astype(float, copy=False), rcond=None)
        coeffs = np.array([self._snap_value(v) for v in coeffs], dtype=float)

        expression = self._build_expression(coeffs)
        preds = coeffs[0] * t0 + coeffs[1] * t1 + coeffs[2] * x1 + coeffs[3] * x2 + coeffs[4]

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }