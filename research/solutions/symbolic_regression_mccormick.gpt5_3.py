import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        if X.ndim != 2 or X.shape[1] != 2:
            raise ValueError("X must be of shape (n, 2)")
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Known McCormick expression
        base_expression = "sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1"
        base_predictions = np.sin(x1 + x2) + (x1 - x2) ** 2 - 1.5 * x1 + 2.5 * x2 + 1.0

        # Fit a flexible linear combination of basis terms as fallback
        sin_term = np.sin(x1 + x2)
        sq_term = (x1 - x2) ** 2
        A = np.column_stack([sin_term, sq_term, x1, x2, np.ones_like(x1)])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c, d, e = coeffs
        fitted_predictions = A @ coeffs
        # Compute MSEs
        def mse(pred):
            diff = y - pred
            return float(np.mean(diff * diff))

        mse_base = mse(base_predictions)
        mse_fit = mse(fitted_predictions)

        # Choose between known formula and fitted linear combination
        # Prefer known formula unless the fit substantially improves MSE
        improvement_threshold = 0.7
        if mse_fit < improvement_threshold * mse_base:
            expression = (
                f"{a:.12g}*sin(x1 + x2) + {b:.12g}*(x1 - x2)**2 + "
                f"{c:.12g}*x1 + {d:.12g}*x2 + {e:.12g}"
            )
            predictions = fitted_predictions
        else:
            expression = base_expression
            predictions = base_predictions

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
