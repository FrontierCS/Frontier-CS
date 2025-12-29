import numpy as np
from itertools import combinations_with_replacement
import os
import tempfile

try:
    from pysr import PySRRegressor

    _HAS_PYSR = True
except Exception:
    PySRRegressor = None
    _HAS_PYSR = False

try:
    import sympy as sp

    _HAS_SYMPY = True
except Exception:
    sp = None
    _HAS_SYMPY = False


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        if X.ndim != 2 or X.shape[1] != 4:
            raise ValueError("X must have shape (n_samples, 4)")

        details = {}

        expression = None
        if _HAS_PYSR:
            try:
                expression, details = self._solve_with_pysr(X, y)
            except Exception:
                expression, details = self._solve_with_fallback(X, y)
        else:
            expression, details = self._solve_with_fallback(X, y)

        return {
            "expression": expression,
            "predictions": None,
            "details": details,
        }

    def _solve_with_pysr(self, X: np.ndarray, y: np.ndarray):
        n_samples = X.shape[0]

        if n_samples <= 500:
            niterations = 120
        elif n_samples <= 2000:
            niterations = 100
        elif n_samples <= 10000:
            niterations = 80
        else:
            niterations = 60

        equation_file = os.path.join(
            tempfile.gettempdir(), "pysr_mixed_polyexp_4d_equations.csv"
        )

        model = PySRRegressor(
            niterations=niterations,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=12,
            population_size=40,
            maxsize=30,
            maxdepth=10,
            verbosity=0,
            progress=False,
            random_state=0,
            equation_file=equation_file,
            model_selection="best",
        )

        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

        best_expr = model.sympy()
        if _HAS_SYMPY and not isinstance(best_expr, sp.Expr):
            # Handle potential list/array outputs
            if isinstance(best_expr, (list, tuple)) and len(best_expr) > 0:
                best_expr = best_expr[0]
            else:
                try:
                    best_expr = sp.sympify(str(best_expr))
                except Exception:
                    pass

        expression = self._sympy_to_python_expression(best_expr)

        details = {}
        try:
            eqs = getattr(model, "equations_", None)
            if eqs is not None and hasattr(eqs, "iloc") and len(eqs) > 0:
                best_row = eqs.iloc[0]
                if "complexity" in best_row:
                    details["complexity"] = int(best_row["complexity"])
        except Exception:
            pass

        return expression, details

    def _sympy_to_python_expression(self, expr):
        if _HAS_SYMPY and isinstance(expr, sp.Expr):
            try:
                expr = sp.simplify(expr)
            except Exception:
                pass
            expr_str = str(expr)
        else:
            expr_str = str(expr)
        expr_str = expr_str.replace("^", "**")
        return expr_str

    def _solve_with_fallback(self, X: np.ndarray, y: np.ndarray):
        F_poly, terms_poly = self._build_poly_features_and_terms(X, degree=2)

        r2 = np.sum(X**2, axis=1)
        r2_expr = "x1**2 + x2**2 + x3**2 + x4**2"

        E1 = np.exp(-r2)
        E2 = np.exp(-0.5 * r2)

        E_exprs = [E1, E2]
        E_strs = [f"exp(-({r2_expr}))", f"exp(-0.5*({r2_expr}))"]

        feature_blocks = [F_poly]
        term_list = list(terms_poly)

        for E_vals, E_str in zip(E_exprs, E_strs):
            FE = F_poly * E_vals[:, None]
            feature_blocks.append(FE)
            for t in terms_poly:
                if t == "1":
                    term_list.append(E_str)
                else:
                    term_list.append(f"{E_str}*({t})")

        A = np.concatenate(feature_blocks, axis=1)

        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        expression = self._coeffs_and_terms_to_expression(coeffs, term_list)

        details = {}

        return expression, details

    def _build_poly_features_and_terms(self, X: np.ndarray, degree: int = 2):
        n_samples, n_features = X.shape
        columns = []
        terms = []

        columns.append(np.ones(n_samples))
        terms.append("1")

        for deg in range(1, degree + 1):
            for idxs in combinations_with_replacement(range(n_features), deg):
                col = np.prod(X[:, idxs], axis=1)
                columns.append(col)
                term_parts = [f"x{j + 1}" for j in idxs]
                term = "*".join(term_parts)
                terms.append(term)

        F = np.column_stack(columns)
        return F, terms

    def _coeffs_and_terms_to_expression(self, coeffs: np.ndarray, terms):
        if coeffs.size == 0:
            return "0.0"

        max_abs = float(np.max(np.abs(coeffs))) if coeffs.size > 0 else 0.0
        tol = 1e-8 * max(1.0, max_abs)

        parts = []
        for c, term in zip(coeffs, terms):
            if not np.isfinite(c):
                continue
            if abs(c) <= tol:
                continue
            c_str = self._format_float(c)
            if term == "1":
                part = c_str
            else:
                part = f"{c_str}*({term})"
            parts.append(part)

        if not parts:
            return "0.0"

        expression = " + ".join(parts)
        return expression

    def _format_float(self, x: float) -> str:
        if not np.isfinite(x):
            return "0.0"
        s = "{:.12g}".format(float(x))
        return s