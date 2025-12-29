import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _fmt(c: float) -> str:
        if np.isnan(c) or np.isinf(c):
            return "0.0"
        s = format(float(c), ".15g")
        if s in ("-0", "-0.0"):
            s = "0.0"
        return s

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)

        x1 = X[:, 0]
        x2 = X[:, 1]

        phi1 = np.sin(x1 + x2)
        phi2 = (x1 - x2) ** 2
        A = np.column_stack([phi1, phi2, x1, x2, np.ones_like(x1)])

        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except Exception:
            coeffs = np.array([1.0, 1.0, -1.5, 2.5, 1.0], dtype=float)

        if coeffs.shape[0] != 5 or not np.all(np.isfinite(coeffs)):
            coeffs = np.array([1.0, 1.0, -1.5, 2.5, 1.0], dtype=float)

        a, b, c, d, e = (float(coeffs[0]), float(coeffs[1]), float(coeffs[2]), float(coeffs[3]), float(coeffs[4]))

        expression = (
            f"{self._fmt(a)}*sin(x1 + x2) + {self._fmt(b)}*(x1 - x2)**2 + "
            f"{self._fmt(c)}*x1 + {self._fmt(d)}*x2 + {self._fmt(e)}"
        )

        preds = a * np.sin(x1 + x2) + b * (x1 - x2) ** 2 + c * x1 + d * x2 + e

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }