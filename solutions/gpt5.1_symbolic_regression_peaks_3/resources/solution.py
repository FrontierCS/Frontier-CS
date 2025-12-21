import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        x1 = X[:, 0]
        x2 = X[:, 1]

        terms = []

        def add_term(expr_str, values):
            terms.append((expr_str, values))

        # Polynomial terms up to degree 3
        add_term("1", np.ones_like(x1))
        add_term("x1", x1)
        add_term("x2", x2)
        add_term("x1**2", x1**2)
        add_term("x2**2", x2**2)
        add_term("x1*x2", x1 * x2)
        add_term("x1**3", x1**3)
        add_term("x2**3", x2**3)
        add_term("x1**2*x2", (x1**2) * x2)
        add_term("x1*x2**2", x1 * (x2**2))

        # Peaks-like exponential terms
        t1 = (1 - x1) ** 2 * np.exp(-x1**2 - (x2 + 1) ** 2)
        add_term("(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2)", t1)

        t2 = (x1 / 5 - x1 ** 3 - x2 ** 5) * np.exp(-x1**2 - x2**2)
        add_term("(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)", t2)

        t3 = np.exp(-(x1 + 1) ** 2 - x2 ** 2)
        add_term("exp(-(x1 + 1)**2 - x2**2)", t3)

        # Extra Gaussian-like term for flexibility
        t4 = np.exp(-x1**2 - (x2 - 1) ** 2)
        add_term("exp(-x1**2 - (x2 - 1)**2)", t4)

        A = np.column_stack([vals for (_, vals) in terms])

        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        y_pred = A @ coeffs

        pieces = []
        tol = 1e-10
        for c, (expr_str, _) in zip(coeffs, terms):
            if abs(c) < tol:
                continue
            coeff_str = f"{c:.16g}"
            piece = f"({coeff_str})*({expr_str})"
            pieces.append(piece)

        if not pieces:
            expression = "0.0"
            y_pred = np.zeros_like(y)
        else:
            expression = " + ".join(pieces)

        return {
            "expression": expression,
            "predictions": y_pred.tolist(),
            "details": {}
        }
