import numpy as np
import sympy as sp


class Solution:
    def __init__(self, **kwargs):
        pass

    def _expression_complexity(self, expr: sp.Expr) -> int:
        binary_ops = 0
        unary_ops = 0

        def _traverse(e):
            nonlocal binary_ops, unary_ops
            if e.is_Atom:
                return
            if isinstance(e, sp.Function):
                unary_ops += 1
            elif isinstance(e, (sp.Add, sp.Mul, sp.Pow)):
                n_args = len(e.args)
                if n_args >= 2:
                    binary_ops += n_args - 1
            for arg in e.args:
                _traverse(arg)

        _traverse(expr)
        return 2 * binary_ops + unary_ops

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n_samples = X.shape[0]

        expression = None
        method = None

        # Try PySR-based symbolic regression
        try:
            from pysr import PySRRegressor

            n = n_samples
            if n <= 2000:
                niterations = 80
                population_size = 40
                populations = 12
                maxsize = 25
            elif n <= 10000:
                niterations = 60
                population_size = 36
                populations = 10
                maxsize = 25
            else:
                niterations = 40
                population_size = 30
                populations = 8
                maxsize = 23

            model = PySRRegressor(
                niterations=niterations,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos"],
                populations=populations,
                population_size=population_size,
                maxsize=maxsize,
                progress=False,
                verbosity=0,
                random_state=42,
            )

            model.fit(X, y, variable_names=["x1", "x2"])
            best_expr_sympy = model.sympy()
            expression = str(best_expr_sympy)
            method = "pysr"
        except Exception:
            expression = None

        # Fallback: handcrafted radial-trigonometric basis with linear regression
        if expression is None:
            x1 = X[:, 0]
            x2 = X[:, 1]
            r2 = x1 ** 2 + x2 ** 2
            r2_str = "(x1**2 + x2**2)"

            features = [
                np.ones_like(r2),
                r2,
                r2 ** 2,
                r2 ** 3,
                np.sin(r2),
                np.sin(2 * r2),
                np.sin(3 * r2),
                np.cos(r2),
                np.cos(2 * r2),
                np.cos(3 * r2),
                r2 * np.sin(r2),
                r2 * np.cos(r2),
                x1,
                x2,
            ]

            exprs = [
                "1",
                r2_str,
                f"{r2_str}**2",
                f"{r2_str}**3",
                f"sin({r2_str})",
                f"sin(2*{r2_str})",
                f"sin(3*{r2_str})",
                f"cos({r2_str})",
                f"cos(2*{r2_str})",
                f"cos(3*{r2_str})",
                f"{r2_str}*sin({r2_str})",
                f"{r2_str}*cos({r2_str})",
                "x1",
                "x2",
            ]

            A = np.column_stack(features)
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            except Exception:
                coeffs = np.zeros(len(features), dtype=float)

            terms = []
            for coef, expr_str in zip(coeffs, exprs):
                c = float(coef)
                if abs(c) < 1e-8:
                    continue
                terms.append(f"({c:.12g})*({expr_str})")
            if terms:
                expression = " + ".join(terms)
            else:
                expression = "0"
            method = "fallback_radial_trig"

        if expression is None:
            expression = "0"
            method = method or "constant_zero"

        # Compute predictions and complexity from the expression via sympy
        predictions = None
        details = {}
        try:
            x1_sym, x2_sym = sp.symbols("x1 x2")
            local_dict = {"sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log}
            expr_sym = sp.sympify(expression, locals=local_dict)
            func = sp.lambdify((x1_sym, x2_sym), expr_sym, "numpy")

            x1_vals = X[:, 0]
            x2_vals = X[:, 1]
            raw_pred = func(x1_vals, x2_vals)
            predictions = np.array(raw_pred, dtype=float)

            if predictions.shape == ():
                predictions = np.full(n_samples, float(predictions))
            elif predictions.shape[0] != n_samples:
                predictions = np.broadcast_to(predictions, (n_samples,))
            predictions = predictions.reshape(n_samples, -1)[:, 0]

            details["complexity"] = self._expression_complexity(expr_sym)
        except Exception:
            predictions = None

        if method is not None:
            details["method"] = method

        return {
            "expression": expression,
            "predictions": predictions.tolist() if predictions is not None else None,
            "details": details,
        }