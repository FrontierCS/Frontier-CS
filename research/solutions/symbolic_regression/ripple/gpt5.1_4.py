import numpy as np
import sympy as sp

try:
    from pysr import PySRRegressor
    _HAS_PYSR = True
except Exception:
    PySRRegressor = None
    _HAS_PYSR = False


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def _is_expression_allowed(self, expr):
        allowed_func_classes = {sp.sin, sp.cos, sp.exp, sp.log}
        for func in expr.atoms(sp.Function):
            if func.func not in allowed_func_classes:
                return False
        return True

    def _evaluate_expression_on_data(self, expression, X):
        x1 = X[:, 0]
        x2 = X[:, 1]
        local_dict = {
            "x1": x1,
            "x2": x2,
            "sin": np.sin,
            "cos": np.cos,
            "exp": np.exp,
            "log": np.log,
        }
        return eval(expression, {"__builtins__": {}}, local_dict)

    def _fit_with_pysr(self, X, y):
        if not _HAS_PYSR:
            return None
        try:
            n_samples = X.shape[0]
            max_samples = 5000
            if n_samples > max_samples:
                rng = np.random.RandomState(0)
                indices = rng.choice(n_samples, size=max_samples, replace=False)
                X_train = X[indices]
                y_train = y[indices]
            else:
                X_train = X
                y_train = y

            model = PySRRegressor(
                niterations=60,
                binary_operators=["+", "-", "*"],
                unary_operators=["sin", "cos"],
                populations=20,
                population_size=50,
                maxsize=30,
                verbosity=0,
                progress=False,
                random_state=0,
            )

            model.fit(X_train, y_train, variable_names=["x1", "x2"])

            if not hasattr(model, "equations_") or len(model.equations_) == 0:
                return None

            best_expr = model.sympy()
            if best_expr is None:
                return None

            if not self._is_expression_allowed(best_expr):
                return None

            expression_str = str(best_expr)

            try:
                preds = model.predict(X)
            except Exception:
                preds = self._evaluate_expression_on_data(expression_str, X)

            preds = np.asarray(preds, dtype=float).reshape(-1)

            return expression_str, preds
        except Exception:
            return None

    def _fallback_trig_radial(self, X, y):
        x1 = X[:, 0]
        x2 = X[:, 1]

        r = np.sqrt(x1 * x1 + x2 * x2)
        r2 = r * r
        r_expr = "((x1**2 + x2**2)**0.5)"

        ones = np.ones_like(y, dtype=float)

        basis_exprs = []
        basis_arrays = []

        basis_exprs.append("1.0")
        basis_arrays.append(ones)

        basis_exprs.append(r_expr)
        basis_arrays.append(r)

        basis_exprs.append(f"{r_expr}**2")
        basis_arrays.append(r2)

        sin_r = np.sin(r)
        cos_r = np.cos(r)
        sin_2r = np.sin(2.0 * r)
        cos_2r = np.cos(2.0 * r)
        sin_3r = np.sin(3.0 * r)
        cos_3r = np.cos(3.0 * r)

        basis_exprs.extend(
            [
                f"sin({r_expr})",
                f"cos({r_expr})",
                f"sin(2.0*{r_expr})",
                f"cos(2.0*{r_expr})",
                f"sin(3.0*{r_expr})",
                f"cos(3.0*{r_expr})",
                f"{r_expr}*sin({r_expr})",
                f"{r_expr}*cos({r_expr})",
                f"{r_expr}*sin(2.0*{r_expr})",
                f"{r_expr}*cos(2.0*{r_expr})",
                f"{r_expr}**2*sin({r_expr})",
                f"{r_expr}**2*cos({r_expr})",
            ]
        )

        basis_arrays.extend(
            [
                sin_r,
                cos_r,
                sin_2r,
                cos_2r,
                sin_3r,
                cos_3r,
                r * sin_r,
                r * cos_r,
                r * sin_2r,
                r * cos_2r,
                r2 * sin_r,
                r2 * cos_r,
            ]
        )

        A = np.column_stack(basis_arrays).astype(float)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        preds = A.dot(coeffs)

        terms = []
        for coeff, expr_str in zip(coeffs, basis_exprs):
            if not np.isfinite(coeff) or abs(coeff) < 1e-8:
                continue
            c_str = f"{coeff:.12g}"
            if expr_str == "1.0":
                term = c_str
            else:
                term = f"({c_str})*({expr_str})"
            terms.append(term)

        if not terms:
            expression = "0.0"
        else:
            expression = " + ".join(terms)

        preds = np.asarray(preds, dtype=float).reshape(-1)

        return expression, preds

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)

        result = self._fit_with_pysr(X, y)
        if result is not None:
            expression, preds = result
        else:
            expression, preds = self._fallback_trig_radial(X, y)

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {},
        }