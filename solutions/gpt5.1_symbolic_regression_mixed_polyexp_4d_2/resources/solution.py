import numpy as np

try:
    from pysr import PySRRegressor
    _HAS_PYSR = True
except Exception:
    PySRRegressor = None
    _HAS_PYSR = False


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def _fit_polynomial_fallback(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        ones = np.ones_like(x1)
        x1_sq = x1 * x1
        x2_sq = x2 * x2
        x3_sq = x3 * x3
        x4_sq = x4 * x4

        x1x2 = x1 * x2
        x1x3 = x1 * x3
        x1x4 = x1 * x4
        x2x3 = x2 * x3
        x2x4 = x2 * x4
        x3x4 = x3 * x4

        A = np.column_stack(
            [
                ones,
                x1,
                x2,
                x3,
                x4,
                x1_sq,
                x2_sq,
                x3_sq,
                x4_sq,
                x1x2,
                x1x3,
                x1x4,
                x2x3,
                x2x4,
                x3x4,
            ]
        )

        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        coeffs = coeffs.ravel()

        def fmt(c):
            return f"{c:.10g}"

        terms = []
        basis = [
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

        for c, b in zip(coeffs, basis):
            if abs(c) < 1e-12:
                continue
            if b == "1":
                terms.append(fmt(c))
            else:
                terms.append(f"({fmt(c)})*{b}")

        if not terms:
            expression = "0"
        else:
            expression = " + ".join(terms)

        predictions = A @ coeffs
        return expression, predictions

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        expression = None
        predictions = None
        details = {}

        if _HAS_PYSR:
            try:
                n_samples = X.shape[0]
                if n_samples <= 2000:
                    niterations = 80
                    maxsize = 30
                else:
                    niterations = 60
                    maxsize = 25

                model_kwargs = {
                    "niterations": niterations,
                    "binary_operators": ["+", "-", "*", "/"],
                    "unary_operators": ["sin", "cos", "exp", "log"],
                    "populations": 20,
                    "population_size": 40,
                    "maxsize": maxsize,
                    "verbosity": 0,
                    "progress": False,
                    "random_state": 42,
                }

                extra_kwargs = self.kwargs.get("pysr_kwargs", {})
                if isinstance(extra_kwargs, dict):
                    model_kwargs.update(extra_kwargs)

                model = PySRRegressor(**model_kwargs)
                model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

                expr_sympy = model.sympy()
                expression = str(expr_sympy)
                predictions = np.asarray(model.predict(X)).ravel()

                try:
                    eqs = getattr(model, "equations_", None)
                    if eqs is not None and len(eqs) > 0:
                        best_idx = eqs["loss"].idxmin()
                        complexity_val = int(eqs.loc[best_idx, "complexity"])
                        details["complexity"] = int(complexity_val)
                except Exception:
                    pass

            except Exception:
                expression = None
                predictions = None
                details = {}

        if expression is None:
            expression, predictions = self._fit_polynomial_fallback(X, y)

        return {
            "expression": expression,
            "predictions": predictions.tolist() if predictions is not None else None,
            "details": details,
        }
