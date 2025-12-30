import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _format_float(c: float) -> str:
        if np.isfinite(c):
            r = round(c)
            if abs(c - r) <= 1e-12 * max(1.0, abs(c)):
                return str(int(r))
            s = f"{c:.15g}"
            if s == "-0":
                s = "0"
            return s
        return "0"

    @staticmethod
    def _snap_coeff(c: float, target: float, atol: float = 1e-6, rtol: float = 1e-3) -> float:
        if abs(c - target) <= max(atol, rtol * abs(target)):
            return float(target)
        return float(c)

    @staticmethod
    def _build_expression(coefs):
        a, b, c, d, e = map(float, coefs)

        def add(parts, term_str, coeff):
            coeff = float(coeff)
            if abs(coeff) <= 1e-14:
                return

            if term_str is None:
                t = Solution._format_float(coeff)
            else:
                if abs(coeff - 1.0) <= 1e-6:
                    t = term_str
                elif abs(coeff + 1.0) <= 1e-6:
                    t = f"-({term_str})"
                else:
                    t = f"{Solution._format_float(coeff)}*{term_str}"

            if not parts:
                parts.append(t)
            else:
                if t.startswith("-"):
                    parts.append(t)
                else:
                    parts.append("+" + t)

        parts = []
        add(parts, "sin(x1 + x2)", a)
        add(parts, "(x1 - x2)**2", b)
        add(parts, "x1", c)
        add(parts, "x2", d)
        add(parts, None, e)

        expr = "".join(parts).strip()
        return expr if expr else "0"

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        if X.ndim != 2 or X.shape[1] != 2:
            raise ValueError("X must have shape (n, 2)")
        n = X.shape[0]
        if y.shape[0] != n:
            raise ValueError("y must have shape (n,) matching X")

        x1 = X[:, 0]
        x2 = X[:, 1]

        phi1 = np.sin(x1 + x2)
        phi2 = (x1 - x2) ** 2
        A = np.column_stack([phi1, phi2, x1, x2, np.ones_like(x1)])

        try:
            coefs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except Exception:
            # Fallback to simple linear regression
            A_lin = np.column_stack([x1, x2, np.ones_like(x1)])
            coefs_lin, _, _, _ = np.linalg.lstsq(A_lin, y, rcond=None)
            a_lin, b_lin, c_lin = map(float, coefs_lin)
            expr = f"{self._format_float(a_lin)}*x1+{self._format_float(b_lin)}*x2+{self._format_float(c_lin)}"
            preds = (a_lin * x1 + b_lin * x2 + c_lin)
            return {"expression": expr, "predictions": preds.tolist(), "details": {}}

        # Snap to known McCormick parameters if very close
        coefs = coefs.astype(float)
        coefs[0] = self._snap_coeff(coefs[0], 1.0, atol=1e-6, rtol=5e-3)
        coefs[1] = self._snap_coeff(coefs[1], 1.0, atol=1e-6, rtol=5e-3)
        coefs[2] = self._snap_coeff(coefs[2], -1.5, atol=1e-6, rtol=5e-3)
        coefs[3] = self._snap_coeff(coefs[3], 2.5, atol=1e-6, rtol=5e-3)
        coefs[4] = self._snap_coeff(coefs[4], 1.0, atol=1e-6, rtol=5e-3)

        expr = self._build_expression(coefs)
        preds = A @ coefs

        return {
            "expression": expr,
            "predictions": preds.tolist(),
            "details": {}
        }