import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Basis functions inspired by the McCormick function
        f1 = np.sin(x1 + x2)
        f2 = (x1 - x2) ** 2
        f3 = x1
        f4 = x2
        f5 = np.ones_like(x1)

        A = np.column_stack([f1, f2, f3, f4, f5])

        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c, d, e = coeffs

        # Build expression string using allowed operations and functions
        expr_terms = [
            f"{a:.12g}*sin(x1 + x2)",
            f"{b:.12g}*(x1 - x2)**2",
            f"{c:.12g}*x1",
            f"{d:.12g}*x2",
            f"{e:.12g}",
        ]
        expression = " + ".join(expr_terms)

        return {
            "expression": expression,
            "predictions": None,
            "details": {}
        }