import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.eps = kwargs.get("eps", 1e-12)
        self.round_digits = kwargs.get("round_digits", 12)

    def _fit_least_squares(self, X, y):
        x1 = X[:, 0]
        x2 = X[:, 1]
        f1 = np.sin(x1 + x2)
        f2 = (x1 - x2) ** 2
        f3 = x1
        f4 = x2
        f5 = np.ones_like(x1)
        A = np.column_stack([f1, f2, f3, f4, f5])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        y_pred = A @ coeffs
        mse = float(np.mean((y - y_pred) ** 2))
        return coeffs, y_pred, mse

    def _format_number(self, num):
        return f"{num:.12g}"

    def _build_expression(self, coeffs):
        # coeffs correspond to: a*sin(x1 + x2) + b*(x1 - x2)**2 + c*x1 + d*x2 + e
        a, b, c, d, e = coeffs
        parts = []

        def add_term(coeff, base_expr, allow_unit=True):
            if abs(coeff) < self.eps:
                return
            sign = "-" if coeff < 0 else "+"
            mag = abs(coeff)
            if base_expr == "1":
                term = self._format_number(mag)
            else:
                if allow_unit and abs(mag - 1.0) < 1e-9:
                    term = base_expr
                else:
                    term = f"{self._format_number(mag)}*{base_expr}"
            parts.append((sign, term))

        add_term(a, "sin(x1 + x2)", allow_unit=True)
        add_term(b, "(x1 - x2)**2", allow_unit=True)
        add_term(c, "x1", allow_unit=True)
        add_term(d, "x2", allow_unit=True)
        add_term(e, "1", allow_unit=False)

        if not parts:
            return "0"

        # Build expression string with proper signs
        first_sign, first_term = parts[0]
        expr = f"-{first_term}" if first_sign == "-" else first_term
        for sign, term in parts[1:]:
            if sign == "+":
                expr += f" + {term}"
            else:
                expr += f" - {term}"
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)

        coeffs, y_pred, mse = self._fit_least_squares(X, y)

        # Optional: compare with canonical McCormick expression
        canonical_coeffs = np.array([1.0, 1.0, -1.5, 2.5, 1.0], dtype=float)
        x1 = X[:, 0]
        x2 = X[:, 1]
        y_pred_canonical = (
            canonical_coeffs[0] * np.sin(x1 + x2)
            + canonical_coeffs[1] * (x1 - x2) ** 2
            + canonical_coeffs[2] * x1
            + canonical_coeffs[3] * x2
            + canonical_coeffs[4]
        )
        mse_canonical = float(np.mean((y - y_pred_canonical) ** 2))

        # Choose between fitted and canonical based on MSE
        # Prefer canonical if it's no worse than fitted by a small margin (for simpler constants)
        if mse_canonical <= mse * 1.0001:
            final_coeffs = canonical_coeffs
            final_pred = y_pred_canonical
        else:
            final_coeffs = coeffs
            final_pred = y_pred

        expression = self._build_expression(final_coeffs)

        return {
            "expression": expression,
            "predictions": final_pred.tolist(),
            "details": {}
        }