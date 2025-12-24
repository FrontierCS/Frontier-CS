import numpy as np
from pysr import PySRRegressor
import warnings

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            dict with keys:
              - "expression": str, a Python-evaluable expression using x1, x2
              - "predictions": list/array of length n (optional)
              - "details": dict with optional "complexity" int
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            model = PySRRegressor(
                niterations=60,
                binary_operators=["+", "-", "*", "/", "**"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=8,
                population_size=40,
                maxsize=30,
                complexity_of_constants=2,
                constraints={
                    "exp": (-1, 10),
                    "log": (1, 10),
                    "**": (-5, 5)
                },
                verbosity=0,
                progress=False,
                deterministic=True,
                warm_start=True,
                early_stop_condition=(
                    "stop_if(loss, complexity) = loss < 1e-8 && complexity < 15"
                ),
                random_state=42,
            )
            
            model.fit(X, y, variable_names=["x1", "x2"])
            
            try:
                best_expr = model.sympy()
                if best_expr is None:
                    expression = "x1 + x2"
                    predictions = X[:, 0] + X[:, 1]
                else:
                    expression = str(best_expr).replace("**", "**")
                    predictions = model.predict(X)
            except:
                expression = "x1 + x2"
                predictions = X[:, 0] + X[:, 1]
            
            complexity = 0
            if expression != "x1 + x2":
                import sympy
                try:
                    expr = sympy.sympify(expression)
                    complexity = self._calculate_complexity(expr)
                except:
                    pass
            
            return {
                "expression": expression,
                "predictions": predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
                "details": {"complexity": complexity}
            }
    
    def _calculate_complexity(self, expr):
        if expr.is_Number:
            return 0
        elif expr.is_Symbol:
            return 0
        elif expr.is_Add or expr.is_Mul:
            return sum(self._calculate_complexity(arg) for arg in expr.args) + 2 * (len(expr.args) - 1)
        elif expr.is_Pow:
            base_comp = self._calculate_complexity(expr.args[0])
            exp_comp = self._calculate_complexity(expr.args[1])
            return base_comp + exp_comp + 2
        elif expr.is_Function:
            return sum(self._calculate_complexity(arg) for arg in expr.args) + 1
        else:
            return 1
