import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.use_pysr = kwargs.get("use_pysr", True)
        self.pysr_niterations = kwargs.get("pysr_niterations", 40)
        self.pysr_populations = kwargs.get("pysr_populations", 15)
        self.pysr_population_size = kwargs.get("pysr_population_size", 33)
        self.pysr_maxsize = kwargs.get("pysr_maxsize", 25)
        self.pysr_random_state = kwargs.get("pysr_random_state", 42)

    def _fit_with_pysr(self, X, y):
        try:
            from pysr import PySRRegressor
        except Exception:
            return None, None, {"solver": "pysr_unavailable"}

        try:
            model = PySRRegressor(
                niterations=self.pysr_niterations,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=self.pysr_populations,
                population_size=self.pysr_population_size,
                maxsize=self.pysr_maxsize,
                verbosity=0,
                progress=False,
                random_state=self.pysr_random_state,
            )
        except Exception:
            return None, None, {"solver": "pysr_unavailable"}

        try:
            model.fit(X, y, variable_names=["x1", "x2"])
            best_expr = model.sympy()
            expression = str(best_expr)
            return expression, None, {"solver": "pysr"}
        except Exception:
            return None, None, {"solver": "pysr_failed"}

    def _fit_fallback(self, X, y):
        x1 = X[:, 0]
        x2 = X[:, 1]
        r2 = x1 ** 2 + x2 ** 2
        r = np.sqrt(r2)

        r2_expr = "(x1**2 + x2**2)"
        r_expr = f"({r2_expr}**0.5)"

        features = []
        feature_exprs = []

        def add_feature(values, expr):
            features.append(values)
            feature_exprs.append(expr)

        ones = np.ones_like(r)
        add_feature(ones, "1.0")
        add_feature(x1, "x1")
        add_feature(x2, "x2")
        add_feature(x1 * x1, "(x1**2)")
        add_feature(x2 * x2, "(x2**2)")
        add_feature(x1 * x2, "(x1*x2)")
        add_feature(r, r_expr)
        add_feature(r2, r2_expr)

        sin_x1 = np.sin(x1)
        sin_x2 = np.sin(x2)
        cos_x1 = np.cos(x1)
        cos_x2 = np.cos(x2)
        add_feature(sin_x1, "sin(x1)")
        add_feature(sin_x2, "sin(x2)")
        add_feature(cos_x1, "cos(x1)")
        add_feature(cos_x2, "cos(x2)")

        sin_r = np.sin(r)
        cos_r = np.cos(r)
        sin_2r = np.sin(2.0 * r)
        cos_2r = np.cos(2.0 * r)
        sin_3r = np.sin(3.0 * r)
        cos_3r = np.cos(3.0 * r)
        sin_5r = np.sin(5.0 * r)
        cos_5r = np.cos(5.0 * r)

        add_feature(sin_r, f"sin({r_expr})")
        add_feature(cos_r, f"cos({r_expr})")
        add_feature(sin_2r, f"sin(2.0*{r_expr})")
        add_feature(cos_2r, f"cos(2.0*{r_expr})")
        add_feature(sin_3r, f"sin(3.0*{r_expr})")
        add_feature(cos_3r, f"cos(3.0*{r_expr})")
        add_feature(sin_5r, f"sin(5.0*{r_expr})")
        add_feature(cos_5r, f"cos(5.0*{r_expr})")

        add_feature(r * sin_r, f"{r_expr}*sin({r_expr})")
        add_feature(r * cos_r, f"{r_expr}*cos({r_expr})")
        add_feature(r2 * sin_r, f"{r2_expr}*sin({r_expr})")
        add_feature(r2 * cos_r, f"{r2_expr}*cos({r_expr})")

        denom = 1.0 + r2
        denom_expr = f"(1.0 + {r2_expr})"
        add_feature(1.0 / denom, f"(1.0/{denom_expr})")
        add_feature(sin_r / denom, f"(sin({r_expr})/{denom_expr})")
        add_feature(cos_r / denom, f"(cos({r_expr})/{denom_expr})")

        if not features:
            expression = "0.0"
            return expression, None, {"solver": "fallback"}

        A = np.column_stack(features)
        m = A.shape[1]
        reg = 1e-6
        AtA = A.T @ A
        diag_idx = np.arange(m)
        AtA[diag_idx, diag_idx] += reg
        Aty = A.T @ y

        try:
            coeffs = np.linalg.solve(AtA, Aty)
        except np.linalg.LinAlgError:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        max_abs_c = float(np.max(np.abs(coeffs))) if coeffs.size > 0 else 0.0
        tol = 1e-8 * (max_abs_c if max_abs_c > 0 else 1.0)

        terms = []
        for c, expr_part in zip(coeffs, feature_exprs):
            if abs(c) <= tol:
                continue
            terms.append(f"({c:.12g})*{expr_part}")

        if not terms:
            expression = "0.0"
        else:
            expression = " + ".join(terms)

        return expression, None, {"solver": "fallback"}

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        expression = None
        predictions = None
        details = {}

        if self.use_pysr:
            expr_pysr, preds_pysr, details_pysr = self._fit_with_pysr(X, y)
            if expr_pysr is not None:
                expression = expr_pysr
                predictions = preds_pysr
                details = details_pysr

        if expression is None:
            expr_fb, preds_fb, details_fb = self._fit_fallback(X, y)
            expression = expr_fb
            predictions = preds_fb
            details = details_fb

        return {
            "expression": expression,
            "predictions": None if predictions is None else np.asarray(predictions).tolist(),
            "details": details,
        }