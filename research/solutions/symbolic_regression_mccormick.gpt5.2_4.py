import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def _snap(self, v: float, tol: float = 1e-10) -> float:
        if not np.isfinite(v):
            return float(v)
        r = round(v)
        if abs(v - r) <= tol:
            return float(int(r))
        for denom in (2, 3, 4, 5, 6, 8, 10, 12):
            num = round(v * denom)
            if abs(v - (num / denom)) <= tol:
                return float(num / denom)
        for tgt in (0.5, -0.5, 1.5, -1.5, 2.5, -2.5):
            if abs(v - tgt) <= tol:
                return float(tgt)
        return float(v)

    def _fmt(self, v: float) -> str:
        if isinstance(v, (int, np.integer)):
            return str(int(v))
        if not np.isfinite(v):
            if np.isnan(v):
                return "0.0"
            return "0.0"
        v = float(v)
        if v == 0.0:
            return "0"
        s = format(v, ".12g")
        if "e" in s or "E" in s:
            s = format(v, ".15g")
        return s

    def _append_term(self, parts, term: str, sign: int):
        if not term:
            return
        if not parts:
            parts.append(term if sign >= 0 else f"-({term})")
        else:
            parts.append(("+ " if sign >= 0 else "- ") + f"({term})")

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        if X.ndim != 2 or X.shape[1] != 2:
            raise ValueError("X must have shape (n, 2)")
        n = X.shape[0]
        if y.shape[0] != n:
            raise ValueError("y must have shape (n,)")

        x1 = X[:, 0]
        x2 = X[:, 1]

        s = np.sin(x1 + x2)
        q = (x1 - x2) ** 2
        A = np.column_stack([s, q, x1, x2, np.ones_like(x1)])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        coeffs = np.array([self._snap(float(v)) for v in coeffs], dtype=float)
        a_sin, a_quad, a_x1, a_x2, a_c = coeffs.tolist()

        parts = []

        def add_scaled(coeff, base_expr):
            coeff = float(coeff)
            if not np.isfinite(coeff) or abs(coeff) < 1e-14:
                return
            if abs(coeff - 1.0) < 1e-12:
                self._append_term(parts, base_expr, +1)
            elif abs(coeff + 1.0) < 1e-12:
                self._append_term(parts, base_expr, -1)
            else:
                sign = +1 if coeff >= 0 else -1
                term = f"{self._fmt(abs(coeff))}*{base_expr}"
                self._append_term(parts, term, sign)

        add_scaled(a_sin, "sin(x1 + x2)")
        add_scaled(a_quad, "(x1 - x2)**2")
        add_scaled(a_x1, "x1")
        add_scaled(a_x2, "x2")

        if np.isfinite(a_c) and abs(a_c) >= 1e-14:
            sign = +1 if a_c >= 0 else -1
            self._append_term(parts, self._fmt(abs(a_c)), sign)

        expression = "0"
        if parts:
            expression = " ".join(parts)

        predictions = a_sin * s + a_quad * q + a_x1 * x1 + a_x2 * x2 + a_c

        details = {
            "coefficients": {
                "sin": float(a_sin),
                "quad": float(a_quad),
                "x1": float(a_x1),
                "x2": float(a_x2),
                "const": float(a_c),
            }
        }

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details,
        }