import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _lstsq_fit_terms(y, terms):
        A = np.column_stack([*terms, np.ones_like(y)])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        pred = A @ coeffs
        mse = float(np.mean((y - pred) ** 2))
        return coeffs, pred, mse

    @staticmethod
    def _compute_peaks_terms(u, v):
        # MATLAB "peaks" components (including canonical constants)
        t1 = 3.0 * (1.0 - u) ** 2 * np.exp(-(u ** 2) - (v + 1.0) ** 2)
        t2 = -10.0 * (u / 5.0 - u ** 3 - v ** 5) * np.exp(-(u ** 2) - (v ** 2))
        t3 = -(1.0 / 3.0) * np.exp(-((u + 1.0) ** 2) - (v ** 2))
        return t1, t2, t3

    @staticmethod
    def _snap(val, tol=1e-10):
        if not np.isfinite(val):
            return val
        if abs(val) <= tol:
            return 0.0
        if abs(val - 1.0) <= tol:
            return 1.0
        if abs(val + 1.0) <= tol:
            return -1.0
        return val

    @staticmethod
    def _fmt_float(val):
        if not np.isfinite(val):
            return "0.0"
        if val == 0.0:
            return "0"
        if val == 1.0:
            return "1"
        if val == -1.0:
            return "-1"
        s = f"{float(val):.16g}"
        if "e" in s or "E" in s:
            s = f"({s})"
        return s

    @staticmethod
    def _build_expression(u_name, v_name, a, b, c, d):
        u = u_name
        v = v_name

        t1 = f"3*(1-({u}))**2*exp(-({u})**2-(({v})+1)**2)"
        t2 = f"-10*(({u})/5-({u})**3-({v})**5)*exp(-({u})**2-({v})**2)"
        t3 = f"-(1/3)*exp(-(({u})+1)**2-({v})**2)"

        parts = []

        def add_term(coeff, term_str):
            coeff = Solution._snap(coeff)
            if coeff == 0.0:
                return
            if coeff == 1.0:
                parts.append(f"({term_str})")
            elif coeff == -1.0:
                parts.append(f"(-({term_str}))")
            else:
                parts.append(f"({Solution._fmt_float(coeff)}*({term_str}))")

        add_term(a, t1)
        add_term(b, t2)
        add_term(c, t3)

        d = Solution._snap(d)
        if d != 0.0:
            parts.append(Solution._fmt_float(d))

        if not parts:
            return "0"

        expr = parts[0]
        for p in parts[1:]:
            if p.startswith("(-") and p.endswith(")"):
                expr = f"({expr})+{p}"
            else:
                expr = f"({expr})+({p})"
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Candidate 1: standard (x1, x2)
        t1, t2, t3 = self._compute_peaks_terms(x1, x2)
        coeffs1, pred1, mse1 = self._lstsq_fit_terms(y, (t1, t2, t3))

        # Candidate 2: swapped (x2, x1)
        s1, s2, s3 = self._compute_peaks_terms(x2, x1)
        coeffs2, pred2, mse2 = self._lstsq_fit_terms(y, (s1, s2, s3))

        if mse2 < mse1:
            a, b, c, d = coeffs2
            expression = self._build_expression("x2", "x1", a, b, c, d)
            predictions = pred2
            mse = mse2
            orientation = "swapped"
            coeffs = coeffs2
        else:
            a, b, c, d = coeffs1
            expression = self._build_expression("x1", "x2", a, b, c, d)
            predictions = pred1
            mse = mse1
            orientation = "standard"
            coeffs = coeffs1

        details = {
            "mse": mse,
            "orientation": orientation,
            "coeffs": [float(v) for v in coeffs],
        }

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details,
        }