import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def _compute_features_variant(self, x1, x2, variant=0):
        if variant == 0:
            g1 = np.exp(-(x1**2 + (x2 + 1.0)**2))
            g2 = np.exp(-(x1**2 + x2**2))
            g3 = np.exp(-((x1 + 1.0)**2 + x2**2))
            phi1 = (1.0 - x1)**2 * g1
            phi2 = (x1/5.0 - x1**3 - x2**5) * g2
            phi3 = g3
            terms = [
                "((1 - x1)**2)*exp(-x1**2 - (x2 + 1)**2)",
                "(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)",
                "exp(-(x1 + 1)**2 - x2**2)"
            ]
        else:
            g1 = np.exp(-(x1**2 + (x2 - 1.0)**2))
            g2 = np.exp(-(x1**2 + x2**2))
            g3 = np.exp(-((x1 - 1.0)**2 + x2**2))
            phi1 = (1.0 - x1)**2 * g1
            phi2 = (x1/5.0 - x1**3 - x2**5) * g2
            phi3 = g3
            terms = [
                "((1 - x1)**2)*exp(-x1**2 - (x2 - 1)**2)",
                "(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)",
                "exp(-(x1 - 1)**2 - x2**2)"
            ]
        A = np.column_stack([phi1, phi2, phi3, np.ones_like(x1)])
        return A, terms

    def _format_coeff(self, c):
        if not np.isfinite(c) or abs(c) < 1e-14:
            return "0"
        s = f"{c:.12g}"
        if s == "-0":
            s = "0"
        return s

    def _fit_model(self, X, y, variant):
        x1 = X[:, 0]
        x2 = X[:, 1]
        A, terms = self._compute_features_variant(x1, x2, variant=variant)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        preds = A @ coeffs
        mse = float(np.mean((y - preds) ** 2))
        return coeffs, preds, mse, terms

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)

        # Fit baseline linear model for optional comparison
        x1 = X[:, 0]
        x2 = X[:, 1]
        B = np.column_stack([x1, x2, np.ones_like(x1)])
        lin_coef, _, _, _ = np.linalg.lstsq(B, y, rcond=None)
        lin_preds = B @ lin_coef
        baseline_mse = float(np.mean((y - lin_preds) ** 2))

        # Try two variants of the peaks-like structure and pick the best
        coeffs0, preds0, mse0, terms0 = self._fit_model(X, y, variant=0)
        coeffs1, preds1, mse1, terms1 = self._fit_model(X, y, variant=1)

        if mse0 <= mse1:
            coeffs, preds, terms = coeffs0, preds0, terms0
        else:
            coeffs, preds, terms = coeffs1, preds1, terms1

        a, b, c, d = coeffs
        fa = self._format_coeff(a)
        fb = self._format_coeff(b)
        fc = self._format_coeff(c)
        fd = self._format_coeff(d)

        expression = f"{fa}*{terms[0]} + {fb}*{terms[1]} + {fc}*{terms[2]} + {fd}"

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }
