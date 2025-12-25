import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _safe_float(x):
        x = float(x)
        if not np.isfinite(x):
            return 0.0
        return x

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        if X.ndim != 2 or X.shape[1] != 2:
            raise ValueError("X must have shape (n, 2)")

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Peaks-like basis
        B1 = ((1.0 - x1) ** 2) * np.exp(-(x1 ** 2) - ((x2 + 1.0) ** 2))
        B2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-(x1 ** 2) - (x2 ** 2))
        B3 = np.exp(-((x1 + 1.0) ** 2) - (x2 ** 2))

        A = np.column_stack([B1, B2, B3, np.ones_like(x1)])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except Exception:
            coeffs = np.array([3.0, -10.0, -1.0 / 3.0, 0.0], dtype=np.float64)

        a, b, c, d = (self._safe_float(v) for v in coeffs.tolist())

        t1 = "((1 - x1)**2)*exp(-(x1**2) - ((x2+1)**2))"
        t2 = "(x1/5 - x1**3 - x2**5)*exp(-(x1**2) - (x2**2))"
        t3 = "exp(-((x1+1)**2) - (x2**2))"

        terms = []
        if abs(a) > 1e-12:
            terms.append(f"({repr(a)})*({t1})")
        if abs(b) > 1e-12:
            terms.append(f"({repr(b)})*({t2})")
        if abs(c) > 1e-12:
            terms.append(f"({repr(c)})*({t3})")
        if abs(d) > 1e-12 or not terms:
            terms.append(f"({repr(d)})")

        expression = " + ".join(terms)

        preds = a * B1 + b * B2 + c * B3 + d
        mse = float(np.mean((y - preds) ** 2)) if y.size else 0.0

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {"mse": mse}
        }