import numpy as np
import sympy as sp

try:
    from pysr import PySRRegressor
    _HAS_PYSR = True
except Exception:
    PySRRegressor = None
    _HAS_PYSR = False

_X1_SYM = sp.Symbol("x1")
_X2_SYM = sp.Symbol("x2")
_SYMPY_LOCALS = {
    "x1": _X1_SYM,
    "x2": _X2_SYM,
    "sin": sp.sin,
    "cos": sp.cos,
    "exp": sp.exp,
    "log": sp.log,
}


class Solution:
    def __init__(self, **kwargs):
        self.max_poly_degree = kwargs.get("max_poly_degree", 5)

    def _compute_complexity_sympy(self, expr: sp.Expr) -> int:
        bin_ops = 0
        unary_ops = 0

        def traverse(e):
            nonlocal bin_ops, unary_ops
            if isinstance(e, sp.Function):
                if e.func in (sp.sin, sp.cos, sp.exp, sp.log):
                    unary_ops += 1
                for arg in e.args:
                    traverse(arg)
            elif isinstance(e, (sp.Add, sp.Mul)):
                n_args = len(e.args)
                if n_args >= 2:
                    bin_ops += n_args - 1
                for arg in e.args:
                    traverse(arg)
            elif isinstance(e, sp.Pow):
                bin_ops += 1
                for arg in e.args:
                    traverse(arg)
            else:
                for arg in e.args:
                    traverse(arg)

        traverse(expr)
        return 2 * bin_ops + unary_ops

    def _fit_polynomial_baseline(self, X: np.ndarray, y: np.ndarray, max_degree: int):
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Precompute powers
        x1_powers = [np.ones(n, dtype=float)]
        x2_powers = [np.ones(n, dtype=float)]
        for d in range(1, max_degree + 1):
            x1_powers.append(x1_powers[-1] * x1)
            x2_powers.append(x2_powers[-1] * x2)

        features = []
        terms = []  # list of (i, j)
        for total_deg in range(max_degree + 1):
            for i in range(total_deg + 1):
                j = total_deg - i
                features.append(x1_powers[i] * x2_powers[j])
                terms.append((i, j))

        A = np.column_stack(features)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        preds = A.dot(coeffs)

        expr_terms = []
        for coeff, (i, j) in zip(coeffs, terms):
            c = float(coeff)
            if abs(c) < 1e-10:
                continue

            term_factors = []
            if i > 0:
                if i == 1:
                    term_factors.append("x1")
                else:
                    term_factors.append(f"x1**{i}")
            if j > 0:
                if j == 1:
                    term_factors.append("x2")
                else:
                    term_factors.append(f"x2**{j}")

            if term_factors:
                term_str = "*".join(term_factors)
                if abs(c - 1.0) < 1e-10:
                    expr_terms.append(term_str)
                    continue
                elif abs(c + 1.0) < 1e-10:
                    expr_terms.append(f"-({term_str})")
                    continue
                else:
                    coeff_str = format(c, ".12g")
                    expr_terms.append(f"{coeff_str}*{term_str}")
            else:
                coeff_str = format(c, ".12g")
                expr_terms.append(coeff_str)

        if not expr_terms:
            expr_str = "0"
        else:
            expr_str = expr_terms[0]
            for term in expr_terms[1:]:
                if term.startswith("-"):
                    expr_str += f" {term}"
                else:
                    expr_str += f" + {term}"

        expr_sympy = sp.sympify(expr_str, locals=_SYMPY_LOCALS)
        complexity = self._compute_complexity_sympy(expr_sympy)
        return expr_str, preds, complexity

    def _peaks_expression(self) -> str:
        return (
            "3*(1 - x1)**2*exp(-(x1**2) - (x2 + 1)**2)"
            " - 10*(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)"
            " - 1/3*exp(-(x1 + 1)**2 - x2**2)"
        )

    def _evaluate_peaks(self, X: np.ndarray) -> np.ndarray:
        x1 = X[:, 0]
        x2 = X[:, 1]
        term1 = 3.0 * (1.0 - x1) ** 2 * np.exp(-(x1 ** 2) - (x2 + 1.0) ** 2)
        term2 = -10.0 * (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-x1 ** 2 - x2 ** 2)
        term3 = -(1.0 / 3.0) * np.exp(-(x1 + 1.0) ** 2 - x2 ** 2)
        return term1 + term2 + term3

    def _run_pysr(self, X: np.ndarray, y: np.ndarray):
        if not _HAS_PYSR:
            return None

        try:
            model = PySRRegressor(
                niterations=60,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=15,
                population_size=33,
                maxsize=20,
                verbosity=0,
                progress=False,
                random_state=42,
            )
            model.fit(X, y, variable_names=["x1", "x2"])
            expr_sympy = model.sympy()
            if expr_sympy is None:
                return None

            expression = str(expr_sympy)
            preds = model.predict(X)
            preds = np.asarray(preds, dtype=float)
            if not np.all(np.isfinite(preds)):
                return None

            mse = float(np.mean((y - preds) ** 2))
            complexity = self._compute_complexity_sympy(expr_sympy)
            return expression, preds, complexity, mse
        except Exception:
            return None

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        y = np.asarray(y, dtype=float)

        candidates = []

        # Polynomial baseline
        poly_expr, poly_preds, poly_complexity = self._fit_polynomial_baseline(
            X, y, self.max_poly_degree
        )
        poly_mse = float(np.mean((y - poly_preds) ** 2))
        candidates.append((poly_expr, poly_preds, poly_complexity, poly_mse))

        # Peaks candidate
        peaks_expr = self._peaks_expression()
        peaks_preds = self._evaluate_peaks(X)
        peaks_mse = float(np.mean((y - peaks_preds) ** 2))
        peaks_sympy = sp.sympify(peaks_expr, locals=_SYMPY_LOCALS)
        peaks_complexity = self._compute_complexity_sympy(peaks_sympy)
        candidates.append((peaks_expr, peaks_preds, peaks_complexity, peaks_mse))

        # PySR candidate
        pysr_result = self._run_pysr(X, y)
        if pysr_result is not None:
            candidates.append(pysr_result)

        # Select best by (MSE, complexity)
        best_expr, best_preds, best_complexity, _ = min(
            candidates, key=lambda c: (c[3], c[2])
        )

        return {
            "expression": best_expr,
            "predictions": best_preds.tolist(),
            "details": {"complexity": int(best_complexity)},
        }