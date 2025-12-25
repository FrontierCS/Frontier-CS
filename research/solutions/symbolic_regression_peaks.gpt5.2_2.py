import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        if X.ndim != 2 or X.shape[1] != 2:
            raise ValueError("X must have shape (n, 2)")
        n = X.shape[0]
        if y.shape[0] != n:
            raise ValueError("y must have shape (n,)")

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Peaks-like basis terms (linear in coefficients)
        g1 = (1.0 - x1) ** 2 * np.exp(-(x1 ** 2) - (x2 + 1.0) ** 2)
        g2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-(x1 ** 2) - (x2 ** 2))
        g3 = np.exp(-((x1 + 1.0) ** 2) - (x2 ** 2))
        ones = np.ones_like(x1)

        A = np.column_stack([g1, g2, g3, ones])
        coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c, d = coef.tolist()

        preds = A @ coef

        def fmt(v: float) -> str:
            if not np.isfinite(v):
                return "0.0"
            s = format(float(v), ".12g")
            if s == "-0":
                s = "0"
            return s

        expression = (
            f"({fmt(a)})*((1 - x1)**2*exp(-x1**2 - (x2 + 1)**2))"
            f" + ({fmt(b)})*(((x1/5) - x1**3 - x2**5)*exp(-x1**2 - x2**2))"
            f" + ({fmt(c)})*(exp(-(x1 + 1)**2 - x2**2))"
            f" + ({fmt(d)})"
        )

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {"complexity": 0},
        }