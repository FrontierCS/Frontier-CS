import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Basis functions inspired by the McCormick function structure
        f1 = np.sin(x1 + x2)
        f2 = (x1 - x2) ** 2
        ones = np.ones_like(x1)

        # Design matrix: [sin(x1+x2), (x1-x2)^2, x1, x2, 1]
        A = np.column_stack([f1, f2, x1, x2, ones])

        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        # Round coefficients for a cleaner expression and use them consistently
        rounded_coeffs = np.array([float(f"{c:.12g}") for c in coeffs])
        a, b, c, d, e = rounded_coeffs

        # Compute predictions using the rounded coefficients
        predictions = a * f1 + b * f2 + c * x1 + d * x2 + e

        # Build the expression string
        a_str, b_str, c_str, d_str, e_str = [f"{c:.12g}" for c in rounded_coeffs]
        expression = (
            f"{a_str}*sin(x1 + x2) + "
            f"{b_str}*(x1 - x2)**2 + "
            f"{c_str}*x1 + "
            f"{d_str}*x2 + "
            f"{e_str}"
        )

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
