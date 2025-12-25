import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        x1 = X[:, 0]
        x2 = X[:, 1]

        try:
            # Peaks-like basis functions
            f1 = (1.0 - x1) ** 2 * np.exp(-(x1 ** 2) - (x2 + 1.0) ** 2)
            f2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-x1 ** 2 - x2 ** 2)
            f3 = np.exp(-(x1 + 1.0) ** 2 - x2 ** 2)

            A = np.column_stack([f1, f2, f3, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a1, a2, a3, a0 = coeffs

            expression = (
                f"({a1:.12f})*(1 - x1)**2*exp(-(x1**2) - (x2 + 1.0)**2)"
                f" + ({a2:.12f})*(x1/5.0 - x1**3 - x2**5)*exp(-x1**2 - x2**2)"
                f" + ({a3:.12f})*exp(-(x1 + 1.0)**2 - x2**2)"
                f" + ({a0:.12f})"
            )
            predictions = (A @ coeffs).tolist()
        except Exception:
            # Fallback: simple linear model
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            expression = f"({a:.12f})*x1 + ({b:.12f})*x2 + ({c:.12f})"
            predictions = (A @ coeffs).tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
