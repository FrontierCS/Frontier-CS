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

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        if _HAVE_PYSR:
            try:
                return self._solve_with_pysr(X, y)
            except Exception:
                pass

        return self._solve_with_trig_basis(X, y)

    def _solve_with_pysr(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=10,
            population_size=25,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
        )
        model.fit(X, y, variable_names=["x1", "x2"])
        best_expr = model.sympy()
        if best_expr is None:
            raise RuntimeError("PySR did not return an expression.")
        expression = str(best_expr)

        return {
            "expression": expression,
            "predictions": None,
            "details": {},
        }

    def _solve_with_trig_basis(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0]
        x2 = X[:, 1]
        n = y.shape[0]

        sin_x1 = np.sin(x1)
        cos_x1 = np.cos(x1)
        sin_x2 = np.sin(x2)
        cos_x2 = np.cos(x2)

        base_exprs = [
            "sin(x1)",               # 0
            "cos(x1)",               # 1
            "sin(x2)",               # 2
            "cos(x2)",               # 3
            "sin(x1)*cos(x2)",       # 4
            "cos(x1)*sin(x2)",       # 5
            "sin(x1 + x2)",          # 6
            "sin(x1 - x2)",          # 7
            "cos(x1 + x2)",          # 8
            "cos(x1 - x2)",          # 9
        ]

        base_vals = [
            sin_x1,
            cos_x1,
            sin_x2,
            cos_x2,
            sin_x1 * cos_x2,
            cos_x1 * sin_x2,
            np.sin(x1 + x2),
            np.sin(x1 - x2),
            np.cos(x1 + x2),
            np.cos(x1 - x2),
        ]

        ones = np.ones(n, dtype=float)

        # Intercept-only candidate
        mean_y = float(np.mean(y))
        best_pred = np.full(n, mean_y, dtype=float)
        best_mse = float(np.mean((y - best_pred) ** 2))
        best_indices = []
        best_coeffs = np.array([mean_y], dtype=float)

        # Single-basis models
        for i, vals in enumerate(base_vals):
            A = np.column_stack([vals, ones])
            coefs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            y_hat = A @ coefs
            mse = float(np.mean((y - y_hat) ** 2))
            if mse < best_mse - 1e-12:
                best_mse = mse
                best_indices = [i]
                best_coeffs = coefs
                best_pred = y_hat

        # Two-basis models
        m = len(base_vals)
        for i in range(m):
            vi = base_vals[i]
            for j in range(i + 1, m):
                vj = base_vals[j]
                A = np.column_stack([vi, vj, ones])
                coefs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                y_hat = A @ coefs
                mse = float(np.mean((y - y_hat) ** 2))
                if mse < best_mse - 1e-12:
                    best_mse = mse
                    best_indices = [i, j]
                    best_coeffs = coefs
                    best_pred = y_hat

        if not best_indices:
            expression = self._format_float(best_coeffs[0])
        else:
            expression = self._build_expression_from_linear(
                best_indices, best_coeffs, base_exprs
            )

        return {
            "expression": expression,
            "predictions": None,
            "details": {},
        }

    def _format_float(self, x: float) -> str:
        if not np.isfinite(x):
            return "0"
        if abs(x) < 1e-12:
            x = 0.0
        return format(float(x), ".12g")

    def _build_expression_from_linear(
        self,
        base_indices,
        coeffs,
        base_exprs,
    ) -> str:
        tol_zero = 1e-6
        tol_one = 1e-3

        feature_coefs = np.array(coeffs[:-1], dtype=float)
        intercept = float(coeffs[-1])

        terms = []

        # Feature terms
        for idx, coef in zip(base_indices, feature_coefs):
            a = float(coef)
            if abs(a) < tol_zero:
                continue

            base_expr = base_exprs[idx]

            sign = 1.0
            if a < 0:
                sign = -1.0
                a = -a

            if abs(a - 1.0) < tol_one:
                coeff_str = ""
            else:
                coeff_str = self._format_float(a)

            if coeff_str:
                core = coeff_str + "*(" + base_expr + ")"
            else:
                core = "(" + base_expr + ")"

            terms.append((sign, core))

        # Intercept term
        if abs(intercept) >= tol_zero:
            c = float(intercept)
            sign = 1.0
            if c < 0:
                sign = -1.0
                c = -c
            const_str = self._format_float(c)
            terms.append((sign, const_str))

        if not terms:
            return "0"

        expr_parts = []
        for k, (sign, core) in enumerate(terms):
            if k == 0:
                if sign > 0:
                    expr_parts.append(core)
                else:
                    expr_parts.append("-(" + core + ")")
            else:
                if sign > 0:
                    expr_parts.append(" + " + core)
                else:
                    expr_parts.append(" - " + core)

        return "".join(expr_parts)