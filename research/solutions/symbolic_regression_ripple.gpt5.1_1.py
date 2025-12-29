import numpy as np
import sympy as sp

try:
    from pysr import PySRRegressor
except Exception:
    PySRRegressor = None


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._pysr_available = PySRRegressor is not None

    def _sanitize_expression_str(self, expr):
        if not isinstance(expr, sp.Expr):
            expr = sp.sympify(expr)
        # Replace sqrt-like powers (exponent 1/2) with **0.5 to avoid sqrt()
        expr_processed = expr.replace(
            lambda e: isinstance(e, sp.Pow) and e.exp == sp.Rational(1, 2),
            lambda e: e.base ** sp.Float(0.5),
        )
        return str(expr_processed)

    def _manual_symbolic_fit(self, X, y):
        x1 = X[:, 0]
        x2 = X[:, 1]

        r2 = x1 ** 2 + x2 ** 2
        r = np.sqrt(r2)

        r2_expr = "(x1**2 + x2**2)"
        r_expr = f"({r2_expr}**0.5)"

        features = []
        feature_exprs = []

        # Intercept
        features.append(np.ones_like(r))
        feature_exprs.append("1.0")

        # Polynomial radial powers without trig: r, r^2
        poly_powers = [1, 2]
        for p in poly_powers:
            features.append(r ** p)
            if p == 1:
                expr = r_expr
            else:
                expr = f"({r_expr}**{p})"
            feature_exprs.append(expr)

        # Trigonometric components with polynomial amplitude
        freqs = [1.0, 2.0, 3.0, 4.0, 5.0]
        amp_powers = [0, 1, 2]

        for p in amp_powers:
            if p == 0:
                amp = np.ones_like(r)
                amp_expr = "1.0"
            elif p == 1:
                amp = r
                amp_expr = r_expr
            else:  # p == 2
                amp = r ** 2
                amp_expr = f"({r_expr}**2)"

            for w in freqs:
                sin_part = np.sin(w * r)
                cos_part = np.cos(w * r)

                # Amplitude * sin(w * r)
                features.append(amp * sin_part)
                base_expr = f"sin({w}*{r_expr})"
                if amp_expr != "1.0":
                    expr = f"({amp_expr})*{base_expr}"
                else:
                    expr = base_expr
                feature_exprs.append(expr)

                # Amplitude * cos(w * r)
                features.append(amp * cos_part)
                base_expr = f"cos({w}*{r_expr})"
                if amp_expr != "1.0":
                    expr = f"({amp_expr})*{base_expr}"
                else:
                    expr = base_expr
                feature_exprs.append(expr)

        A = np.column_stack(features)
        if A.ndim == 1:
            A = A.reshape(-1, 1)

        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except Exception:
            expression = "x1 + x2"
            predictions = X[:, 0] + X[:, 1]
            return expression, predictions

        abs_coeffs = np.abs(coeffs)
        max_abs = float(np.max(abs_coeffs)) if coeffs.size else 0.0
        if max_abs == 0.0 or not np.isfinite(max_abs):
            threshold = 0.0
        else:
            threshold = max_abs * 1e-4

        terms = []
        for c, expr in zip(coeffs, feature_exprs):
            if not np.isfinite(c):
                continue
            if abs(c) < threshold:
                continue
            coef_str = f"{c:.12g}"
            if expr == "1.0":
                term = coef_str
            else:
                term = f"({coef_str})*({expr})"
            terms.append(term)

        if not terms:
            expression = "0.0"
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

        if self._pysr_available:
            try:
                model = PySRRegressor(
                    niterations=40,
                    binary_operators=["+", "-", "*", "/", "^"],
                    unary_operators=["sin", "cos"],
                    populations=15,
                    population_size=33,
                    maxsize=25,
                    verbosity=0,
                    progress=False,
                    random_state=42,
                )
                model.fit(X, y, variable_names=["x1", "x2"])
                best_expr = model.sympy()
                expression = self._sanitize_expression_str(best_expr)
                predictions = model.predict(X)
                details["source"] = "pysr"
            except Exception:
                expression, predictions = self._manual_symbolic_fit(X, y)
                details["source"] = "manual_fallback"
        else:
            expression, predictions = self._manual_symbolic_fit(X, y)
            details["source"] = "manual_fallback"

        if isinstance(predictions, np.ndarray):
            predictions = predictions.tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": details,
        }