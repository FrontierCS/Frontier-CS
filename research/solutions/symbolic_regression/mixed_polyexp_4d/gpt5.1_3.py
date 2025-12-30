import numpy as np

try:
    from pysr import PySRRegressor
except Exception:
    PySRRegressor = None


class Solution:
    def __init__(self, **kwargs):
        self.params = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or X.shape[1] < 4:
            raise ValueError("X must be a 2D array with at least 4 columns.")
        if X.shape[1] > 4:
            X = X[:, :4]
        y = np.asarray(y, dtype=float).ravel()

        expression = None
        preds = None
        details = {}

        if PySRRegressor is not None:
            try:
                expression, preds = self._solve_with_pysr(X, y)
                details["method"] = "pysr"
            except Exception:
                expression, preds = self._solve_with_polynomial_basis(X, y)
                details["method"] = "poly_fallback"
        else:
            expression, preds = self._solve_with_polynomial_basis(X, y)
            details["method"] = "poly_fallback"

        predictions = preds.tolist() if preds is not None else None

        return {
            "expression": expression,
            "predictions": predictions,
            "details": details,
        }

    def _solve_with_pysr(self, X: np.ndarray, y: np.ndarray):
        n = X.shape[0]

        if n <= 2000:
            niterations = 50
            populations = 20
            population_size = 40
            maxsize = 30
        elif n <= 8000:
            niterations = 40
            populations = 18
            population_size = 36
            maxsize = 30
        else:
            niterations = 35
            populations = 16
            population_size = 32
            maxsize = 28

        model = PySRRegressor(
            niterations=niterations,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=populations,
            population_size=population_size,
            maxsize=maxsize,
            verbosity=0,
            progress=False,
            random_state=42,
        )

        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

        best_expr = model.sympy()
        expression = str(best_expr)

        try:
            preds = model.predict(X)
            preds = np.asarray(preds, dtype=float).ravel()
        except Exception:
            preds = None

        return expression, preds

    def _solve_with_polynomial_basis(self, X: np.ndarray, y: np.ndarray):
        n, d = X.shape
        n_vars = 4
        max_degree = 4 if n >= 30 else 3
        include_gaussian = True

        max_d = max_degree

        X_powers = []
        for j in range(n_vars):
            col = X[:, j]
            powers = [np.ones_like(col)]
            for deg in range(1, max_d + 1):
                powers.append(col ** deg)
            X_powers.append(powers)

        term_descs = [("const",)]

        for total_deg in range(1, max_d + 1):
            for e1 in range(total_deg + 1):
                for e2 in range(total_deg - e1 + 1):
                    for e3 in range(total_deg - e1 - e2 + 1):
                        e4 = total_deg - e1 - e2 - e3
                        exps = (e1, e2, e3, e4)
                        term_descs.append(("poly", exps))

        if include_gaussian:
            term_descs.append(("gauss_base",))
            term_descs.append(("gauss_r2",))

        m = len(term_descs)
        A = np.empty((n, m), dtype=float)

        if include_gaussian:
            if max_d >= 2:
                r2 = (
                    X_powers[0][2]
                    + X_powers[1][2]
                    + X_powers[2][2]
                    + X_powers[3][2]
                )
            else:
                r2 = (
                    X[:, 0] ** 2
                    + X[:, 1] ** 2
                    + X[:, 2] ** 2
                    + X[:, 3] ** 2
                )
            g = np.exp(-r2)
        else:
            r2 = None
            g = None

        for idx, desc in enumerate(term_descs):
            kind = desc[0]
            if kind == "const":
                A[:, idx] = 1.0
            elif kind == "poly":
                e1, e2, e3, e4 = desc[1]
                term = np.ones(n, dtype=float)
                for var_idx, exp in enumerate((e1, e2, e3, e4)):
                    if exp > 0:
                        term *= X_powers[var_idx][exp]
                A[:, idx] = term
            elif kind == "gauss_base":
                A[:, idx] = g
            elif kind == "gauss_r2":
                A[:, idx] = r2 * g

        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        coeff_threshold = 1e-8
        coeffs_used = coeffs.copy()
        small = np.abs(coeffs_used) < coeff_threshold
        coeffs_used[small] = 0.0

        preds = A @ coeffs_used

        expression = self._build_expression_from_coeffs(coeffs_used, term_descs)

        return expression, preds

    def _monomial_expr(self, exps):
        parts = []
        for i, p in enumerate(exps):
            if p == 0:
                continue
            var = f"x{i + 1}"
            if p == 1:
                parts.append(var)
            else:
                parts.append(f"{var}**{p}")
        if not parts:
            return "1"
        return " * ".join(parts)

    def _r2_expr(self):
        return "x1**2 + x2**2 + x3**2 + x4**2"

    def _build_expression_from_coeffs(self, coeffs, term_descs):
        terms = []
        r2_expr = self._r2_expr()
        for coef, desc in zip(coeffs, term_descs):
            if coef == 0.0:
                continue
            cstr = f"{coef:.12g}"
            kind = desc[0]
            if kind == "const":
                term_expr = "1"
            elif kind == "poly":
                term_expr = self._monomial_expr(desc[1])
            elif kind == "gauss_base":
                term_expr = f"exp(-({r2_expr}))"
            elif kind == "gauss_r2":
                term_expr = f"({r2_expr})*exp(-({r2_expr}))"
            else:
                continue
            if term_expr == "1":
                terms.append(f"{cstr}")
            else:
                terms.append(f"({cstr})*({term_expr})")
        if not terms:
            return "0.0"
        return " + ".join(terms)