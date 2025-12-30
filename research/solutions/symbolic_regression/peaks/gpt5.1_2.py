import numpy as np

try:
    from pysr import PySRRegressor
    _HAS_PYSR = True
except Exception:
    PySRRegressor = None
    _HAS_PYSR = False


class Solution:
    def __init__(self, **kwargs):
        pass

    def _fit_peaks_basis(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0].astype(float)
        x2 = X[:, 1].astype(float)

        term1 = (1.0 - x1) ** 2 * np.exp(-x1 ** 2 - (x2 + 1.0) ** 2)
        term2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-x1 ** 2 - x2 ** 2)
        term3 = np.exp(-(x1 + 1.0) ** 2 - x2 ** 2)

        A = np.column_stack((term1, term2, term3, np.ones_like(x1)))
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        y_pred = A @ coeffs
        diff = y - y_pred
        mse = float(np.mean(diff ** 2))

        c1, c2, c3, c4 = [repr(float(v)) for v in coeffs]

        expression = (
            f"{c1}*(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2)"
            f" + {c2}*(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)"
            f" + {c3}*exp(-(x1 + 1)**2 - x2**2)"
            f" + {c4}"
        )

        return expression, y_pred, mse

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        expr_basis, y_pred_basis, mse_basis = self._fit_peaks_basis(X, y)
        var_y = float(np.var(y))

        use_pysr = False
        if _HAS_PYSR and var_y > 0.0:
            if mse_basis > 0.1 * var_y:
                use_pysr = True

        if use_pysr:
            try:
                model = PySRRegressor(
                    niterations=40,
                    binary_operators=["+", "-", "*", "/"],
                    unary_operators=["sin", "cos", "exp", "log"],
                    populations=15,
                    population_size=33,
                    maxsize=25,
                    verbosity=0,
                    progress=False,
                    random_state=42,
                )
                model.fit(X, y, variable_names=["x1", "x2"])
                best_expr = model.sympy()
                expression = str(best_expr)
                predictions = model.predict(X)
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {}
                }
            except Exception:
                pass

        return {
            "expression": expr_basis,
            "predictions": y_pred_basis.tolist(),
            "details": {}
        }