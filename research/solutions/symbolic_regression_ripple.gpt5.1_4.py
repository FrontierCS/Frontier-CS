import numpy as np

try:
    from pysr import PySRRegressor
    _HAVE_PYSR = True
except Exception:
    _HAVE_PYSR = False


class Solution:
    def __init__(self, use_pysr: bool = True, **kwargs):
        self.use_pysr = bool(use_pysr) and _HAVE_PYSR

    def _fit_with_pysr(self, X: np.ndarray, y: np.ndarray):
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=15,
            population_size=33,
            maxsize=25,
            progress=False,
            verbosity=0,
            random_state=0,
            procs=0,
        )
        model.fit(X, y, variable_names=["x1", "x2"])

        # Best expression as sympy object, then to string
        best_expr = model.sympy()
        expression = str(best_expr)

        details = {"method": "pysr"}
        try:
            equations = model.equations_
            if "loss" in equations.columns:
                best_row = equations.loc[equations["loss"].idxmin()]
                if "complexity" in best_row:
                    details["complexity"] = int(best_row["complexity"])
        except Exception:
            pass

        predictions = model.predict(X)
        return expression, predictions, details

    def _fit_with_manual_basis(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]

        r2 = x1**2 + x2**2
        r = np.sqrt(r2 + 1e-6)

        features = []
        exprs = []

        def add_feature(expr_str, values):
            exprs.append(expr_str)
            features.append(values)

        r2_expr = "((x1**2) + (x2**2))"
        r_expr = f"exp(0.5*log({r2_expr} + 1e-6))"

        add_feature("1.0", np.ones_like(x1))
        add_feature(r_expr, r)
        add_feature(r2_expr, r2)
        add_feature(f"sin({r_expr})", np.sin(r))
        add_feature(f"cos({r_expr})", np.cos(r))
        add_feature(f"sin(2*{r_expr})", np.sin(2 * r))
        add_feature(f"cos(2*{r_expr})", np.cos(2 * r))
        add_feature(f"sin({r_expr})/(1.0 + {r_expr})", np.sin(r) / (1.0 + r))
        add_feature(f"cos({r_expr})/(1.0 + {r_expr})", np.cos(r) / (1.0 + r))
        add_feature(f"sin({r2_expr})", np.sin(r2))
        add_feature(f"cos({r2_expr})", np.cos(r2))
        add_feature(f"sin(2*{r2_expr})", np.sin(2 * r2))
        add_feature(f"cos(2*{r2_expr})", np.cos(2 * r2))
        add_feature(f"sin({r2_expr})/(1.0 + {r2_expr})", np.sin(r2) / (1.0 + r2))
        add_feature(f"cos({r2_expr})/(1.0 + {r2_expr})", np.cos(r2) / (1.0 + r2))
        add_feature(
            f"sin({r2_expr})/(1.0 + ({r2_expr}**2))",
            np.sin(r2) / (1.0 + r2**2),
        )
        add_feature(
            f"cos({r2_expr})/(1.0 + ({r2_expr}**2))",
            np.cos(r2) / (1.0 + r2**2),
        )
        add_feature(f"{r2_expr}/(1.0 + {r2_expr})", r2 / (1.0 + r2))

        A = np.column_stack(features)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        abs_coeffs = np.abs(coeffs)
        max_abs = abs_coeffs.max() if abs_coeffs.size > 0 else 0.0

        if max_abs == 0.0:
            expression = "0.0"
            predictions = np.zeros_like(y)
            details = {"method": "manual_basis"}
            return expression, predictions, details

        threshold = max_abs * 1e-3
        keep_mask = abs_coeffs >= threshold
        if not np.any(keep_mask):
            keep_mask[np.argmax(abs_coeffs)] = True

        filtered_coeffs = np.where(keep_mask, coeffs, 0.0)

        terms = []
        for c, expr_str in zip(filtered_coeffs, exprs):
            if c == 0.0:
                continue
            c_str = f"{c:.16g}"
            terms.append(f"({c_str})*({expr_str})")

        if not terms:
            expression = "0.0"
        else:
            expression = " + ".join(terms)

        predictions = A @ filtered_coeffs
        details = {"method": "manual_basis"}
        return expression, predictions, details

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        if self.use_pysr:
            try:
                expression, predictions, details = self._fit_with_pysr(X, y)
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": details,
                }
            except Exception:
                pass

        expression, predictions, details = self._fit_with_manual_basis(X, y)
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details,
        }
