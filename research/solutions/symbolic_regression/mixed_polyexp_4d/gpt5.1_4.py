import numpy as np

try:
    from pysr import PySRRegressor
    _HAVE_PYSR = True
except Exception:
    PySRRegressor = None
    _HAVE_PYSR = False


class Solution:
    def __init__(self, **kwargs):
        pass

    def _fit_pysr(self, X: np.ndarray, y: np.ndarray):
        if not _HAVE_PYSR:
            return None, None

        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=20,
            population_size=40,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
        )

        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        best_expr = model.sympy()
        expression = str(best_expr)

        try:
            predictions = model.predict(X)
        except Exception:
            predictions = None

        return expression, predictions

    def _fallback_polynomial(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        ones = np.ones_like(x1)

        features = [
            ones,
            x1,
            x2,
            x3,
            x4,
            x1 ** 2,
            x2 ** 2,
            x3 ** 2,
            x4 ** 2,
            x1 * x2,
            x1 * x3,
            x1 * x4,
            x2 * x3,
            x2 * x4,
            x3 * x4,
        ]

        A = np.column_stack(features)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        terms = [
            "1",
            "x1",
            "x2",
            "x3",
            "x4",
            "x1**2",
            "x2**2",
            "x3**2",
            "x4**2",
            "x1*x2",
            "x1*x3",
            "x1*x4",
            "x2*x3",
            "x2*x4",
            "x3*x4",
        ]

        expression_parts = []
        for c, term in zip(coeffs, terms):
            if abs(c) < 1e-8:
                continue
            c_val = float(c)
            c_abs_str = f"{abs(c_val):.12g}"
            if term == "1":
                core = c_abs_str
            else:
                core = f"{c_abs_str}*{term}"
            if not expression_parts:
                if c_val < 0:
                    expression_parts.append(f"-{core}")
                else:
                    expression_parts.append(core)
            else:
                if c_val < 0:
                    expression_parts.append(f" - {core}")
                else:
                    expression_parts.append(f" + {core}")

        if not expression_parts:
            expression = "0"
        else:
            expression = "".join(expression_parts)

        predictions = A @ coeffs
        return expression, predictions

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        expression = None
        predictions = None

        if _HAVE_PYSR:
            try:
                expression, predictions = self._fit_pysr(X, y)
            except Exception:
                expression = None
                predictions = None

        if expression is None:
            expression, predictions = self._fallback_polynomial(X, y)

        if isinstance(predictions, np.ndarray):
            predictions = predictions.tolist()
        elif predictions is not None:
            try:
                predictions = list(predictions)
            except Exception:
                predictions = None

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {},
        }