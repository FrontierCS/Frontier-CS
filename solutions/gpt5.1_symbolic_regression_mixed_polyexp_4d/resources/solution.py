import numpy as np

try:
    from pysr import PySRRegressor
    _HAVE_PYSR = True
except Exception:
    PySRRegressor = None
    _HAVE_PYSR = False


class Solution:
    def __init__(self, use_pysr: bool = True, pysr_params: dict | None = None, **kwargs):
        self.use_pysr = bool(use_pysr) and _HAVE_PYSR
        self.pysr_params = pysr_params or {}

    def _solve_with_pysr(self, X: np.ndarray, y: np.ndarray):
        if not _HAVE_PYSR:
            raise RuntimeError("PySR is not available in this environment.")

        # Default PySR parameters tuned for 4D poly-exp style problems
        params = {
            "niterations": 60,
            "binary_operators": ["+", "-", "*", "/"],
            "unary_operators": ["sin", "cos", "exp"],
            "populations": 20,
            "population_size": 40,
            "maxsize": 35,
            "verbosity": 0,
            "progress": False,
            "random_state": 0,
        }
        # Allow overriding defaults
        for key, val in self.pysr_params.items():
            params[key] = val

        model = PySRRegressor(**params)
        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

        expr_obj = model.sympy()
        expression = str(expr_obj)
        if not isinstance(expression, str) or not expression.strip():
            raise RuntimeError("PySR returned an invalid expression.")

        try:
            preds = model.predict(X)
            preds = np.asarray(preds, dtype=float).ravel()
        except Exception:
            preds = None

        details = {"method": "pysr"}
        return expression, preds, details

    def _solve_with_fallback(self, X: np.ndarray, y: np.ndarray):
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        ones = np.ones(n, dtype=float)
        r2 = x1**2 + x2**2 + x3**2 + x4**2
        g = np.exp(-r2)
        g_str = "exp(-((x1**2 + x2**2 + x3**2 + x4**2)))"

        features = []
        names = []

        def add_feature(arr, name):
            features.append(arr)
            names.append(name)

        # Constant term
        add_feature(ones, "1")

        variables = [("x1", x1), ("x2", x2), ("x3", x3), ("x4", x4)]

        # Linear terms
        for name, arr in variables:
            add_feature(arr, name)

        # Quadratic terms
        for name, arr in variables:
            add_feature(arr * arr, f"{name}**2")

        # Cross terms
        for i in range(len(variables)):
            name_i, arr_i = variables[i]
            for j in range(i + 1, len(variables)):
                name_j, arr_j = variables[j]
                add_feature(arr_i * arr_j, f"{name_i}*{name_j}")

        # Gaussian term
        add_feature(g, g_str)

        # Gaussian * linear terms
        for name, arr in variables:
            add_feature(arr * g, f"{name}*{g_str}")

        # Gaussian * cross terms
        for i in range(len(variables)):
            name_i, arr_i = variables[i]
            for j in range(i + 1, len(variables)):
                name_j, arr_j = variables[j]
                add_feature(arr_i * arr_j * g, f"{name_i}*{name_j}*{g_str}")

        A = np.column_stack(features)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        preds = A @ coeffs

        # Build expression string from coefficients and feature names
        eps = 1e-12
        parts = []
        for c, name in zip(coeffs, names):
            if not np.isfinite(c) or abs(c) < eps:
                continue
            c_float = float(c)
            c_str = f"{c_float:.12g}"
            if name == "1":
                term = c_str
            else:
                if c_str == "1":
                    term = name
                elif c_str == "-1":
                    term = f"-{name}"
                else:
                    term = f"{c_str}*{name}"
            parts.append(term)

        if not parts:
            expression = "0.0"
        else:
            expression = parts[0]
            for term in parts[1:]:
                term_strip = term.lstrip()
                if term_strip.startswith("-"):
                    expression += " - " + term_strip[1:]
                else:
                    expression += " + " + term_strip

        details = {"method": "fallback_polyexp_lstsq"}
        return expression, preds, details

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        expression = None
        predictions = None
        details: dict = {}

        if self.use_pysr:
            try:
                expression, predictions, details = self._solve_with_pysr(X, y)
            except Exception:
                expression = None
                predictions = None
                details = {}

        if expression is None:
            expression, predictions, fb_details = self._solve_with_fallback(X, y)
            details.update(fb_details)

        return {
            "expression": expression,
            "predictions": predictions.tolist() if isinstance(predictions, np.ndarray) else None,
            "details": details,
        }
