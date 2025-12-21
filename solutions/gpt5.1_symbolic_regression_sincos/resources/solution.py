import numpy as np

try:
    from pysr import PySRRegressor
    _HAS_PYSR = True
except Exception:
    PySRRegressor = None
    _HAS_PYSR = False


class Solution:
    def __init__(self, **kwargs):
        # PySR hyperparameters (can be overridden via kwargs)
        self.niterations = kwargs.get("niterations", 40)
        self.populations = kwargs.get("populations", 15)
        self.population_size = kwargs.get("population_size", 33)
        self.maxsize = kwargs.get("maxsize", 25)
        self.random_state = kwargs.get("random_state", 42)
        self.use_pysr = kwargs.get("use_pysr", True)

    def _fit_pysr(self, X: np.ndarray, y: np.ndarray):
        if not _HAS_PYSR:
            return None
        try:
            model = PySRRegressor(
                niterations=self.niterations,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=self.populations,
                population_size=self.population_size,
                maxsize=self.maxsize,
                verbosity=0,
                progress=False,
                random_state=self.random_state,
            )
            model.fit(X, y, variable_names=["x1", "x2"])

            # Try to get best equation and its complexity
            best_expr = None
            complexity = None
            try:
                best_eq = model.get_best()
                if hasattr(best_eq, "sympy_format"):
                    best_expr = best_eq.sympy_format
                else:
                    best_expr = model.sympy()
                if hasattr(best_eq, "complexity"):
                    complexity = int(best_eq.complexity)
            except Exception:
                best_expr = model.sympy()
                try:
                    eqs = model.equations_
                    if eqs is not None and "complexity" in eqs.columns and len(eqs) > 0:
                        complexity = int(eqs.iloc[0]["complexity"])
                except Exception:
                    complexity = None

            expression = str(best_expr)
            predictions = model.predict(X)

            details = {}
            if complexity is not None:
                details["complexity"] = complexity

            return expression, predictions, details
        except Exception:
            return None

    def _fit_fallback(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]

        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)
        ones = np.ones_like(x1)

        # Linear regression on basic trig basis
        A = np.column_stack([s1, c1, s2, c2, ones])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a_s1, a_c1, a_s2, a_c2, c0 = coeffs

        def simplify_coeff(val, tol=1e-3):
            targets = [0.0, 1.0, -1.0, 0.5, -0.5, 2.0, -2.0]
            for t in targets:
                if abs(val - t) < tol:
                    return t
            return val

        coeffs_simplified = [
            simplify_coeff(a_s1),
            simplify_coeff(a_c1),
            simplify_coeff(a_s2),
            simplify_coeff(a_c2),
            simplify_coeff(c0),
        ]
        a_s1, a_c1, a_s2, a_c2, c0 = coeffs_simplified

        terms = []

        def add_term(coef, base):
            if abs(coef) < 1e-8:
                return
            coef_str = f"{abs(coef):.10f}"
            if not terms:
                sign = "-" if coef < 0 else ""
                terms.append(f"{sign}{coef_str}*{base}")
            else:
                op = "-" if coef < 0 else "+"
                terms.append(f"{op} {coef_str}*{base}")

        add_term(a_s1, "sin(x1)")
        add_term(a_c1, "cos(x1)")
        add_term(a_s2, "sin(x2)")
        add_term(a_c2, "cos(x2)")

        # Constant term
        if abs(c0) >= 1e-8:
            c_str = f"{abs(c0):.10f}"
            if not terms:
                sign = "-" if c0 < 0 else ""
                terms.append(f"{sign}{c_str}")
            else:
                op = "-" if c0 < 0 else "+"
                terms.append(f"{op} {c_str}")

        if not terms:
            expression = "0.0"
        else:
            expression = " ".join(terms)

        predictions = (
            a_s1 * s1 + a_c1 * c1 + a_s2 * s2 + a_c2 * c2 + c0 * ones
        )

        return expression, predictions

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        if self.use_pysr and _HAS_PYSR:
            result = self._fit_pysr(X, y)
            if result is not None:
                expression, predictions, details = result
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": details,
                }

        # Fallback: manual trig regression
        expression, predictions = self._fit_fallback(X, y)
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {},
        }
