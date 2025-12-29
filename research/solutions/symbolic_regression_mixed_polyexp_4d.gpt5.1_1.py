import numpy as np
import sympy as sp

try:
    from pysr import PySRRegressor
    _HAVE_PYSR = True
except Exception:
    PySRRegressor = None
    _HAVE_PYSR = False


class Solution:
    def __init__(self, **kwargs):
        self.use_pysr = kwargs.get("use_pysr", _HAVE_PYSR)
        self.pysr_niterations = kwargs.get("pysr_niterations", 60)
        self.pysr_maxsize = kwargs.get("pysr_maxsize", 30)
        self.pysr_populations = kwargs.get("pysr_populations", 20)
        self.pysr_population_size = kwargs.get("pysr_population_size", 40)
        self.random_state = kwargs.get("random_state", 42)

    def _fit_polyexp_baseline(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        r2 = x1**2 + x2**2 + x3**2 + x4**2
        e = np.exp(-r2)

        one = np.ones_like(x1)
        monos_data = [
            one,
            x1,
            x2,
            x3,
            x4,
            x1**2,
            x2**2,
            x3**2,
            x4**2,
            x1 * x2,
            x1 * x3,
            x1 * x4,
            x2 * x3,
            x2 * x4,
            x3 * x4,
        ]

        features_data = [m * e for m in monos_data] + monos_data
        A = np.column_stack(features_data)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        preds = A @ coeffs

        r2_str = "x1**2 + x2**2 + x3**2 + x4**2"
        exp_str = f"exp(-({r2_str}))"
        monom_strs = [
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

        feature_terms_str = []
        for ms in monom_strs:
            if ms == "1":
                feature_terms_str.append(exp_str)
            else:
                feature_terms_str.append(f"{exp_str}*({ms})")
        feature_terms_str.extend(monom_strs)

        tol = 1e-8
        terms_expr = []
        for coef, term_str in zip(coeffs, feature_terms_str):
            if not np.isfinite(coef):
                continue
            if abs(coef) < tol:
                continue
            coef_str = f"{coef:.12g}"
            if term_str == "1":
                term_expr = coef_str
            else:
                term_expr = f"{coef_str}*({term_str})"
            terms_expr.append(term_expr)

        if not terms_expr:
            expression = "0"
        else:
            expression = " + ".join(terms_expr)

        return expression, preds

    def _fit_pysr(self, X: np.ndarray, y: np.ndarray):
        if not self.use_pysr or PySRRegressor is None:
            return None, None

        model = PySRRegressor(
            niterations=self.pysr_niterations,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp"],
            populations=self.pysr_populations,
            population_size=self.pysr_population_size,
            maxsize=self.pysr_maxsize,
            verbosity=0,
            progress=False,
            random_state=self.random_state,
        )

        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        best_expr_sympy = model.sympy()
        if best_expr_sympy is None:
            return None, None
        expression = str(best_expr_sympy)
        preds = np.asarray(model.predict(X), dtype=float)
        return expression, preds

    def _estimate_complexity(self, expr_str: str) -> int:
        if not expr_str:
            return 0
        try:
            expr = sp.sympify(expr_str)
            c = int(sp.count_ops(expr, visual=False))
            return c
        except Exception:
            return len(expr_str)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        baseline_expr, baseline_pred = self._fit_polyexp_baseline(X, y)
        best_expr = baseline_expr
        best_pred = baseline_pred
        best_mse = float(np.mean((baseline_pred - y) ** 2))
        best_complexity = self._estimate_complexity(baseline_expr)

        if self.use_pysr and PySRRegressor is not None:
            try:
                pysr_expr, pysr_pred = self._fit_pysr(X, y)
            except Exception:
                pysr_expr, pysr_pred = None, None

            if pysr_expr is not None and pysr_pred is not None and np.all(
                np.isfinite(pysr_pred)
            ):
                pysr_mse = float(np.mean((pysr_pred - y) ** 2))
                pysr_complexity = self._estimate_complexity(pysr_expr)

                # Choose PySR solution if it has clearly better MSE,
                # or if MSE is similar but complexity is significantly lower.
                if pysr_mse + 1e-9 < best_mse:
                    best_expr = pysr_expr
                    best_pred = pysr_pred
                    best_mse = pysr_mse
                    best_complexity = pysr_complexity
                else:
                    rel_diff = (pysr_mse - best_mse) / max(best_mse, 1e-12)
                    if rel_diff <= 0.02 and pysr_complexity + 5 < best_complexity:
                        best_expr = pysr_expr
                        best_pred = pysr_pred
                        best_mse = pysr_mse
                        best_complexity = pysr_complexity

        return {
            "expression": best_expr,
            "predictions": best_pred.tolist(),
            "details": {"complexity": int(best_complexity)},
        }