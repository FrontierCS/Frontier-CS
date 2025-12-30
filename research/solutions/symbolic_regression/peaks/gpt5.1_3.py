import numpy as np
import sympy as sp


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def _compute_complexity(self, expression: str):
        try:
            expr = sp.sympify(
                expression,
                locals={"sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log},
            )
        except Exception:
            return None

        binary_ops = 0
        unary_ops = 0

        for node in sp.preorder_traversal(expr):
            if isinstance(node, (sp.Add, sp.Mul)):
                # n-ary operations count as (n-1) binary ops
                binary_ops += max(len(node.args) - 1, 0)
            elif isinstance(node, sp.Pow):
                binary_ops += 1
            elif isinstance(node, sp.Function):
                if node.func in (sp.sin, sp.cos, sp.exp, sp.log):
                    unary_ops += 1

        return 2 * binary_ops + unary_ops

    def _fallback_peaks(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Basis functions inspired by MATLAB's peaks function
        t1 = (1.0 - x1) ** 2 * np.exp(-x1 ** 2 - (x2 + 1.0) ** 2)
        t2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-x1 ** 2 - x2 ** 2)
        t3 = np.exp(-(x1 + 1.0) ** 2 - x2 ** 2)
        ones = np.ones_like(x1)

        A = np.column_stack([t1, t2, t3, ones])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        c1, c2, c3, c0 = coeffs

        if not np.all(np.isfinite(coeffs)):
            # Very robust fallback: simple linear regression
            A_lin = np.column_stack([x1, x2, ones])
            coeffs_lin, _, _, _ = np.linalg.lstsq(A_lin, y, rcond=None)
            a, b, c = coeffs_lin
            predictions = A_lin @ coeffs_lin
            expression = f"({a:.12g})*x1 + ({b:.12g})*x2 + ({c:.12g})"
            complexity = self._compute_complexity(expression)
            return expression, predictions, complexity

        predictions = A @ coeffs

        def fmt(val):
            return f"{float(val):.12g}"

        expression = (
            f"({fmt(c1)})*(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2)"
            f" + ({fmt(c2)})*(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)"
            f" + ({fmt(c3)})*exp(-(x1 + 1)**2 - x2**2)"
            f" + ({fmt(c0)})"
        )

        complexity = self._compute_complexity(expression)
        return expression, predictions, complexity

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        if X.ndim != 2 or X.shape[1] != 2:
            raise ValueError("X must have shape (n, 2)")

        expression = None
        predictions = None
        complexity = None

        # Try to use PySR if available and functioning
        try:
            from pysr import PySRRegressor

            pysr_available = True
        except Exception:
            pysr_available = False

        if pysr_available:
            try:
                model = PySRRegressor(
                    niterations=60,
                    binary_operators=["+", "-", "*", "/", "pow"],
                    unary_operators=["sin", "cos", "exp"],
                    populations=15,
                    population_size=33,
                    maxsize=25,
                    verbosity=0,
                    progress=False,
                    random_state=42,
                )

                model.fit(X, y, variable_names=["x1", "x2"])

                best_expr = model.sympy()
                if isinstance(best_expr, dict):
                    if "best" in best_expr:
                        expr_sym = best_expr["best"]
                    else:
                        expr_sym = list(best_expr.values())[0]
                else:
                    expr_sym = best_expr

                expression = str(expr_sym)

                try:
                    predictions = model.predict(X)
                except Exception:
                    predictions = None

                complexity = self._compute_complexity(expression)
            except Exception:
                expression = None
                predictions = None
                complexity = None

        # Fallback to parametric peaks-like model if PySR is unavailable or failed
        if expression is None:
            expression, predictions, complexity = self._fallback_peaks(X, y)

        result = {"expression": expression}

        if predictions is not None:
            result["predictions"] = np.asarray(predictions, dtype=float).tolist()
        else:
            result["predictions"] = None

        details = {}
        if complexity is not None:
            try:
                details["complexity"] = int(complexity)
            except Exception:
                pass

        result["details"] = details
        return result