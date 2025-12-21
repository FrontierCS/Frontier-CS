import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).ravel()

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Peaks-like basis functions
        t1 = (1.0 - x1) ** 2 * np.exp(-(x1 ** 2) - (x2 + 1.0) ** 2)
        t2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-x1 ** 2 - x2 ** 2)
        t3 = np.exp(-(x1 + 1.0) ** 2 - x2 ** 2)

        A = np.column_stack([t1, t2, t3])

        # Linear least squares to fit coefficients
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c = coeffs

        expression = (
            f"({repr(a)})*(1 - x1)**2*exp(-(x1**2) - (x2 + 1)**2)"
            f" + ({repr(b)})*(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)"
            f" + ({repr(c)})*exp(-(x1 + 1)**2 - x2**2)"
        )

        predictions = A @ coeffs

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
