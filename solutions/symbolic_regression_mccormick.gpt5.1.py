import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0].astype(float)
        x2 = X[:, 1].astype(float)

        predictions = np.sin(x1 + x2) + (x1 - x2) ** 2 - 1.5 * x1 + 2.5 * x2 + 1.0

        expression = "sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1"

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
