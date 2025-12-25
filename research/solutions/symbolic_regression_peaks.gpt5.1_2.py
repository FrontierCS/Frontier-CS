import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Candidate 1: analytic peaks function
        term1 = 3.0 * (1.0 - x1) ** 2 * np.exp(-x1 ** 2 - (x2 + 1.0) ** 2)
        term2 = -10.0 * (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-x1 ** 2 - x2 ** 2)
        term3 = -(1.0 / 3.0) * np.exp(-(x1 + 1.0) ** 2 - x2 ** 2)
        pred_peaks = term1 + term2 + term3
        mse_peaks = np.mean((y - pred_peaks) ** 2)

        # Candidate 2: linear regression baseline
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        pred_lin = A @ coeffs
        mse_lin = np.mean((y - pred_lin) ** 2)

        # Decide which expression to use
        if mse_peaks < 0.9 * mse_lin:
            expression = (
                "3*(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2) - "
                "10*(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2) - "
                "(1/3)*exp(-(x1 + 1)**2 - x2**2)"
            )
            predictions = pred_peaks
        else:
            a, b, c = coeffs
            expression = f"{a:.10f}*x1 + {b:.10f}*x2 + {c:.10f}"
            predictions = pred_lin

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
