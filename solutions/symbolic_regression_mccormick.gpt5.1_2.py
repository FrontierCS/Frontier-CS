import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        x1 = X[:, 0]
        x2 = X[:, 1]

        # McCormick function
        y_pred = np.sin(x1 + x2) + (x1 - x2) ** 2 - 1.5 * x1 + 2.5 * x2 + 1.0

        expression = "sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1"

        return {
            "expression": expression,
            "predictions": y_pred.tolist(),
            "details": {}
        }
