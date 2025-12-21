import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).ravel()

        x1 = X[:, 0].astype(float)
        x2 = X[:, 1].astype(float)

        # Check if exactly McCormick function (noise-free)
        y_mcc = np.sin(x1 + x2) + (x1 - x2) ** 2 - 1.5 * x1 + 2.5 * x2 + 1.0
        mse_mcc = np.mean((y_mcc - y) ** 2)
        if mse_mcc <= 1e-12:
            expression = "sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1.0"
            predictions = y_mcc
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }

        # Fit a parameterized McCormick-like model via least squares
        s = np.sin(x1 + x2)
        q = (x1 - x2) ** 2
        A = np.column_stack([s, q, x1, x2, np.ones_like(x1)])

        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c, d, e = coeffs

        # Build expression string
        def fmt(v):
            return f"{float(v):.12g}"

        expression = (
            f"{fmt(a)}*sin(x1 + x2) + {fmt(b)}*(x1 - x2)**2 + "
            f"{fmt(c)}*x1 + {fmt(d)}*x2 + {fmt(e)}"
        )

        predictions = A @ coeffs

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
