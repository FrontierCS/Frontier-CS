import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)

        x1 = X[:, 0]
        x2 = X[:, 1]

        f1 = np.sin(x1 + x2)
        f2 = (x1 - x2) ** 2
        f3 = x1
        f4 = x2
        f5 = np.ones_like(x1)

        A = np.column_stack((f1, f2, f3, f4, f5))

        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a1, a2, a3, a4, a5 = coeffs
            expression = (
                f"({repr(a1)})*sin(x1 + x2) + "
                f"({repr(a2)})*(x1 - x2)**2 + "
                f"({repr(a3)})*x1 + "
                f"({repr(a4)})*x2 + "
                f"({repr(a5)})"
            )
            predictions = A.dot(coeffs)
        except Exception:
            A_lin = np.column_stack((x1, x2, np.ones_like(x1)))
            coeffs_lin, _, _, _ = np.linalg.lstsq(A_lin, y, rcond=None)
            a, b, c = coeffs_lin
            expression = f"({repr(a)})*x1 + ({repr(b)})*x2 + ({repr(c)})"
            predictions = A_lin.dot(coeffs_lin)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }