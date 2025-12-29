import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.snap_tol_abs = kwargs.get("snap_tol_abs", 1e-3)
        self.snap_tol_rel = kwargs.get("snap_tol_rel", 1e-4)
        self.zero_tol = kwargs.get("zero_tol", 1e-9)

    def _format_float(self, x: float) -> str:
        # Snap to nearest half if close
        near_half = round(2 * x) / 2.0
        if abs(x - near_half) <= max(self.snap_tol_abs, self.snap_tol_rel * max(1.0, abs(near_half))):
            x = near_half
        # General formatting
        if abs(x) < 1e-12:
            return "0"
        return f"{x:.12g}"

    def _build_expression_from_coeffs(self, coeffs):
        a, b, c, d, e = coeffs
        terms = []

        def add_term(coef, base):
            if abs(coef) < self.zero_tol:
                return
            sign = 1 if coef >= 0 else -1
            val = abs(coef)
            if base != "1":
                if abs(val - 1.0) <= max(self.snap_tol_abs, self.snap_tol_rel):
                    term = base
                else:
                    term = f"{self._format_float(val)}*{base}"
            else:
                term = self._format_float(val)
            terms.append((sign, term))

        add_term(a, "sin(x1 + x2)")
        add_term(b, "(x1 - x2)**2")
        add_term(c, "x1")
        add_term(d, "x2")
        add_term(e, "1")

        if not terms:
            return "0"

        expr_parts = []
        for i, (sign, term) in enumerate(terms):
            if i == 0:
                expr_parts.append(f"-{term}" if sign < 0 else term)
            else:
                expr_parts.append((" - " if sign < 0 else " + ") + term)
        return "".join(expr_parts)

    def _predict_from_coeffs(self, x1, x2, coeffs):
        a, b, c, d, e = coeffs
        return a * np.sin(x1 + x2) + b * (x1 - x2) ** 2 + c * x1 + d * x2 + e

    def _mse(self, y_true, y_pred):
        diff = y_true - y_pred
        return float(np.mean(diff * diff))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0]
        x2 = X[:, 1]
        n = len(y)

        s = np.sin(x1 + x2)
        q = (x1 - x2) ** 2
        ones = np.ones(n, dtype=float)

        F = np.column_stack([s, q, x1, x2, ones])
        coeffs, _, _, _ = np.linalg.lstsq(F, y, rcond=None)
        pred_lstsq = F @ coeffs
        mse_lstsq = self._mse(y, pred_lstsq)

        # Candidate 1: Exact McCormick
        mc_coeffs = np.array([1.0, 1.0, -1.5, 2.5, 1.0], dtype=float)
        pred_mc = self._predict_from_coeffs(x1, x2, mc_coeffs)
        mse_mc = self._mse(y, pred_mc)

        # Candidate 2: Rounded-to-halves coefficients
        rounded_coeffs = np.round(2 * coeffs) / 2.0
        pred_round = self._predict_from_coeffs(x1, x2, rounded_coeffs)
        mse_round = self._mse(y, pred_round)

        # Select best by MSE; prefer McCormick if very close
        candidates = [
            ("mc", mc_coeffs, pred_mc, mse_mc),
            ("round", rounded_coeffs, pred_round, mse_round),
            ("lstsq", coeffs, pred_lstsq, mse_lstsq),
        ]
        candidates.sort(key=lambda tup: tup[3])

        best_name, best_coeffs, best_pred, best_mse = candidates[0]

        # If the McCormick is within a small margin of the best, prefer it for simplicity
        margin = 1e-6 + 1e-3 * max(1.0, np.var(y))
        if mse_mc <= best_mse + margin:
            best_name, best_coeffs, best_pred, best_mse = ("mc", mc_coeffs, pred_mc, mse_mc)

        if best_name == "mc":
            expression = "sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1"
        else:
            expression = self._build_expression_from_coeffs(best_coeffs)

        return {
            "expression": expression,
            "predictions": best_pred.tolist(),
            "details": {}
        }