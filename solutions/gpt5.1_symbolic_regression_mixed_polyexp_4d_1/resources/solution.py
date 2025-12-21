import numpy as np
import re


def _estimate_complexity(expression: str) -> int:
    if not expression:
        return 0
    unary_patterns = r'\b(?:sin|cos|exp|log)\b'
    unary_count = len(re.findall(unary_patterns, expression))

    pow_count = expression.count('**')
    tmp = expression.replace('**', '')

    plus_count = len(re.findall(r'(?<=[\w\)])\s*\+\s*(?=[\w\(])', tmp))
    minus_count = len(re.findall(r'(?<=[\w\)])\s*\-\s*(?=[\w\(])', tmp))
    mul_count = len(re.findall(r'(?<=[\w\)])\s*\*\s*(?=[\w\(])', tmp))
    div_count = len(re.findall(r'(?<=[\w\)])\s*\/\s*(?=[\w\(])', tmp))

    binary_total = pow_count + plus_count + minus_count + mul_count + div_count
    return 2 * binary_total + unary_count


class Solution:
    def __init__(self, use_pysr: bool = True, **kwargs):
        self.use_pysr = use_pysr

    def _fit_pysr(self, X: np.ndarray, y: np.ndarray):
        try:
            from pysr import PySRRegressor
        except Exception as e:
            raise RuntimeError("PySR not available") from e

        n_samples = X.shape[0]

        if n_samples <= 2000:
            niterations = 60
            populations = 20
            population_size = 40
            maxsize = 30
        elif n_samples <= 5000:
            niterations = 45
            populations = 18
            population_size = 36
            maxsize = 32
        else:
            niterations = 35
            populations = 16
            population_size = 32
            maxsize = 32

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

        try:
            best_expr_sympy = model.sympy()
            expression = str(best_expr_sympy)
        except Exception:
            # Fallback: basic representation from equations_ if sympy() fails
            equations = getattr(model, "equations_", None)
            if equations is not None and len(equations) > 0:
                try:
                    if "loss" in equations.columns:
                        equations = equations.sort_values("loss", ascending=True)
                    elif "score" in equations.columns:
                        equations = equations.sort_values("score", ascending=False)
                    best = equations.iloc[0]
                    expression = str(best.get("sympy_format", best.get("equation", "x1 + x2 + x3 + x4")))
                except Exception:
                    expression = "x1 + x2 + x3 + x4"
            else:
                expression = "x1 + x2 + x3 + x4"

        try:
            predictions = model.predict(X)
        except Exception:
            predictions = None

        complexity = None
        try:
            equations = getattr(model, "equations_", None)
            if equations is not None and len(equations) > 0:
                if "loss" in equations.columns:
                    equations_sorted = equations.sort_values("loss", ascending=True)
                elif "score" in equations.columns:
                    equations_sorted = equations.sort_values("score", ascending=False)
                else:
                    equations_sorted = equations
                if "complexity" in equations_sorted.columns:
                    complexity = int(equations_sorted["complexity"].iloc[0])
        except Exception:
            complexity = None

        if complexity is None:
            complexity = _estimate_complexity(expression)

        if predictions is None:
            # As a last resort, we will not return predictions; caller may recompute
            pass

        return expression, predictions, complexity

    def _manual_basis_regression(self, X: np.ndarray, y: np.ndarray):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        features = []
        exprs = []

        def add_feature(arr, expr):
            features.append(arr)
            exprs.append(expr)

        # Constant term
        ones = np.ones_like(x1)
        add_feature(ones, "1.0")

        # Linear terms
        add_feature(x1, "x1")
        add_feature(x2, "x2")
        add_feature(x3, "x3")
        add_feature(x4, "x4")

        # Quadratic terms
        x1_2 = x1 * x1
        x2_2 = x2 * x2
        x3_2 = x3 * x3
        x4_2 = x4 * x4

        add_feature(x1_2, "x1**2")
        add_feature(x2_2, "x2**2")
        add_feature(x3_2, "x3**2")
        add_feature(x4_2, "x4**2")

        # Cross quadratic terms
        add_feature(x1 * x2, "x1*x2")
        add_feature(x1 * x3, "x1*x3")
        add_feature(x1 * x4, "x1*x4")
        add_feature(x2 * x3, "x2*x3")
        add_feature(x2 * x4, "x2*x4")
        add_feature(x3 * x4, "x3*x4")

        # Gaussian-like exponential damping
        sum_sq = x1_2 + x2_2 + x3_2 + x4_2
        g_all = np.exp(-sum_sq)
        g1 = np.exp(-x1_2)
        g2 = np.exp(-x2_2)
        g3 = np.exp(-x3_2)
        g4 = np.exp(-x4_2)
        g12 = np.exp(-(x1_2 + x2_2))
        g34 = np.exp(-(x3_2 + x4_2))

        add_feature(g_all, "exp(-(x1**2 + x2**2 + x3**2 + x4**2))")
        add_feature(g1, "exp(-x1**2)")
        add_feature(g2, "exp(-x2**2)")
        add_feature(g3, "exp(-x3**2)")
        add_feature(g4, "exp(-x4**2)")
        add_feature(g12, "exp(-(x1**2 + x2**2))")
        add_feature(g34, "exp(-(x3**2 + x4**2))")

        # Linear terms times global Gaussian
        add_feature(x1 * g_all, "x1*exp(-(x1**2 + x2**2 + x3**2 + x4**2))")
        add_feature(x2 * g_all, "x2*exp(-(x1**2 + x2**2 + x3**2 + x4**2))")
        add_feature(x3 * g_all, "x3*exp(-(x1**2 + x2**2 + x3**2 + x4**2))")
        add_feature(x4 * g_all, "x4*exp(-(x1**2 + x2**2 + x3**2 + x4**2))")

        A = np.column_stack(features)

        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=1e-6)
        except np.linalg.LinAlgError:
            # Fallback to simple linear regression
            A_simple = np.column_stack([ones, x1, x2, x3, x4])
            coeffs_simple, _, _, _ = np.linalg.lstsq(A_simple, y, rcond=1e-6)
            c0, c1, c2, c3, c4 = coeffs_simple
            expression = (
                f"{c0:.12g}"
                f" + ({c1:.12g})*x1"
                f" + ({c2:.12g})*x2"
                f" + ({c3:.12g})*x3"
                f" + ({c4:.12g})*x4"
            )
            predictions = A_simple @ coeffs_simple
            complexity = _estimate_complexity(expression)
            return expression, predictions, complexity

        # Prune very small coefficients
        tol = 1e-8
        coeffs_pruned = coeffs.copy()
        coeffs_pruned[np.abs(coeffs_pruned) < tol] = 0.0

        terms = []
        for c, expr in zip(coeffs_pruned, exprs):
            if abs(c) < tol:
                continue
            if expr == "1.0":
                term = f"{c:.12g}"
            else:
                if abs(c - 1.0) < 1e-12:
                    term = f"({expr})"
                elif abs(c + 1.0) < 1e-12:
                    term = f"(-({expr}))"
                else:
                    term = f"({c:.12g})*({expr})"
            terms.append(term)

        if not terms:
            expression = "0.0"
            predictions = np.zeros_like(y)
            complexity = 0
            return expression, predictions, complexity

        expression = " + ".join(terms)
        predictions = A @ coeffs_pruned
        complexity = _estimate_complexity(expression)

        return expression, predictions, complexity

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        expression = None
        predictions = None
        details = {}

        used_pysr = False

        if self.use_pysr:
            try:
                expression, predictions, complexity = self._fit_pysr(X, y)
                used_pysr = True
                if complexity is not None:
                    details["complexity"] = int(complexity)
            except Exception:
                used_pysr = False

        if not used_pysr:
            expression, predictions, complexity = self._manual_basis_regression(X, y)
            if complexity is not None:
                details["complexity"] = int(complexity)

        if isinstance(predictions, np.ndarray):
            predictions_out = predictions.tolist()
        else:
            predictions_out = predictions

        return {
            "expression": expression,
            "predictions": predictions_out,
            "details": details,
        }
