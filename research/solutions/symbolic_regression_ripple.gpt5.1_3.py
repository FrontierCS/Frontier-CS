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

    def _fit_fallback_radial_trig(self, X, y):
        x1 = X[:, 0]
        x2 = X[:, 1]
        r = np.sqrt(x1 ** 2 + x2 ** 2)

        max_freq = int(self.kwargs.get("fallback_max_freq", 5))
        poly_degree = int(self.kwargs.get("fallback_poly_degree", 3))

        features = [np.ones_like(r)]
        for d in range(1, poly_degree + 1):
            features.append(r ** d)

        for k in range(1, max_freq + 1):
            kr = k * r
            sin_kr = np.sin(kr)
            cos_kr = np.cos(kr)
            features.append(sin_kr)
            features.append(cos_kr)
            features.append(r * sin_kr)
            features.append(r * cos_kr)

        A = np.column_stack(features)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        preds = A @ coeffs

        terms = []
        idx = 0
        c0 = coeffs[idx]
        idx += 1
        if abs(c0) > 1e-12:
            terms.append(f"{c0:.12g}")

        r_expr = "(x1**2 + x2**2)**0.5"

        def add_term(coef, term):
            if abs(coef) <= 1e-12:
                return
            terms.append(f"({coef:.12g})*({term})")

        for d in range(1, poly_degree + 1):
            cd = coeffs[idx]
            idx += 1
            add_term(cd, f"{r_expr}**{d}")

        for k in range(1, max_freq + 1):
            c_sin = coeffs[idx]
            c_cos = coeffs[idx + 1]
            c_rsin = coeffs[idx + 2]
            c_rcos = coeffs[idx + 3]
            idx += 4

            add_term(c_sin, f"sin({k}*{r_expr})")
            add_term(c_cos, f"cos({k}*{r_expr})")
            add_term(c_rsin, f"{r_expr}*sin({k}*{r_expr})")
            add_term(c_rcos, f"{r_expr}*cos({k}*{r_expr})")

        if not terms:
            expression = "0.0"
        else:
            expression = " + ".join(terms)

        return expression, preds

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n_samples = X.shape[0]

        expression = None
        predictions = None
        details = {}

        if _HAS_PYSR:
            try:
                if "niterations" in self.kwargs:
                    niterations = int(self.kwargs["niterations"])
                else:
                    if n_samples <= 5000:
                        niterations = 80
                    elif n_samples <= 20000:
                        niterations = 60
                    else:
                        niterations = 40

                populations = int(self.kwargs.get("populations", 20))
                population_size = int(self.kwargs.get("population_size", 40))
                maxsize = int(self.kwargs.get("maxsize", 25))
                binary_operators = self.kwargs.get(
                    "binary_operators", ["+", "-", "*", "/", "^"]
                )
                unary_operators = self.kwargs.get(
                    "unary_operators", ["sin", "cos", "exp", "log"]
                )
                verbosity = int(self.kwargs.get("verbosity", 0))
                progress = bool(self.kwargs.get("progress", False))
                random_state = int(self.kwargs.get("random_state", 42))

                model = PySRRegressor(
                    niterations=niterations,
                    binary_operators=binary_operators,
                    unary_operators=unary_operators,
                    populations=populations,
                    population_size=population_size,
                    maxsize=maxsize,
                    verbosity=verbosity,
                    progress=progress,
                    random_state=random_state,
                )

                model.fit(X, y, variable_names=["x1", "x2"])
                expr_sympy = model.sympy()
                expression = str(expr_sympy)
                predictions = model.predict(X)
                details["method"] = "pysr"
            except Exception:
                expression = None
                predictions = None

        if expression is None or predictions is None:
            expression, predictions = self._fit_fallback_radial_trig(X, y)
            details["method"] = details.get("method", "fallback_radial_trig")

        predictions = np.asarray(predictions).ravel()

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details,
        }
