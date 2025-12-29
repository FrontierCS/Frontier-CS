import numpy as np
from pysr import PySRRegressor
import sympy
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module='pysr')
warnings.filterwarnings("ignore", category=FutureWarning)

class Solution:
    def __init__(self, **kwargs):
        self.random_state = 42

    def _round_sympy_expr(self, expr, precision):
        if not hasattr(expr, 'xreplace'):
            return expr
            
        return expr.xreplace({
            n: sympy.Float(round(float(n), precision))
            for n in expr.atoms(sympy.Float)
        })

    def _fallback_linear(self, X: np.ndarray, y: np.ndarray) -> dict:
        try:
            A = np.c_[X, np.ones(X.shape[0])]
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            variables = ["x1", "x2", "x3", "x4", "1"]
            terms = [f"{c:.6f}*{v}" for c, v in zip(coeffs, variables)]
            expression = " + ".join(terms).replace("*1", "").replace("+-", "- ")
            
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
            a, b, c, d, e = coeffs
            predictions = a * x1 + b * x2 + c * x3 + d * x4 + e

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }
        except np.linalg.LinAlgError:
            mean_y = np.mean(y)
            expression = f"{mean_y:.6f}"
            predictions = np.full_like(y, mean_y)
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=150,
            populations=32,
            population_size=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "cos", "sin", "square(x)=x*x"],
            extra_sympy_mappings={"square": lambda x: x**2},
            maxsize=35,
            procs=8,
            turbo=True,
            annealing=True,
            optimizer_nrestarts=3,
            batching=True,
            batch_size=max(128, X.shape[0] // 20) if X.shape[0] > 1000 else X.shape[0],
            early_stop_condition="stop_if(loss, 1e-6)",
            verbosity=0,
            progress=False,
            random_state=self.random_state,
            complexity_of_constants=0.1,
            temp_equation_file=True,
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        except Exception:
            return self._fallback_linear(X, y)

        if not hasattr(model, 'equations_') or model.equations_.shape[0] == 0:
            return self._fallback_linear(X, y)
        
        best_eq_row = model.get_best()
        
        expression_sympy = best_eq_row['sympy_format']
        complexity = best_eq_row['complexity']

        try:
            expression_rounded = self._round_sympy_expr(expression_sympy, 6)
            expression_str = str(expression_rounded)
        except (AttributeError, TypeError, Exception):
            expression_str = str(expression_sympy)
        
        predictions = model.predict(X, index=best_eq_row.name)

        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": {"complexity": int(complexity)}
        }