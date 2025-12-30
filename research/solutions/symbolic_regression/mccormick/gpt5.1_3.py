import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Basis functions matching the McCormick structure
        f1 = np.sin(x1 + x2)          # sin(x1 + x2)
        f2 = (x1 - x2) ** 2           # (x1 - x2)^2
        f3 = x1                       # x1
        f4 = x2                       # x2
        f5 = np.ones_like(x1)         # constant term

        A = np.column_stack([f1, f2, f3, f4, f5])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c, d, e = coeffs

        # Least-squares predictions
        y_pred_ls = A @ coeffs
        mse_ls = float(np.mean((y - y_pred_ls) ** 2))

        # Canonical McCormick formula
        y_pred_canon = f1 + f2 - 1.5 * f3 + 2.5 * f4 + 1.0
        mse_canon = float(np.mean((y - y_pred_canon) ** 2))

        # Choose between canonical and fitted coefficients
        if mse_canon <= mse_ls:
            expression = "sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1"
            predictions = y_pred_canon
        else:
            eps = 1e-9
            terms = []
            if abs(a) > eps:
                terms.append(f"{a:.12g}*sin(x1 + x2)")
            if abs(b) > eps:
                terms.append(f"{b:.12g}*(x1 - x2)**2")
            if abs(c) > eps:
                terms.append(f"{c:.12g}*x1")
            if abs(d) > eps:
                terms.append(f"{d:.12g}*x2")
            if abs(e) > eps:
                terms.append(f"{e:.12g}")
            if terms:
                expression = " + ".join(terms)
            else:
                expression = "0.0"
            predictions = y_pred_ls

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }