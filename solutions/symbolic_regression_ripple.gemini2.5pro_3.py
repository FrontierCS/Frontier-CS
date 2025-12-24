import numpy as np
from pysr import PySRRegressor
import sympy
from sympy import Function, Wild

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Learns a symbolic expression for the given data using PySR.
        """
        
        model = PySRRegressor(
            # Search configuration
            niterations=100,
            populations=32,
            population_size=50,
            
            # Environment configuration
            procs=8,
            timeout_in_seconds=60 * 10,
            
            # Expression structure configuration
            maxsize=30,
            binary_operators=["+", "*", "-", "/"],
            # A custom 'square' operator helps discover quadratic terms efficiently.
            unary_operators=["cos", "sin", "exp", "log", "square(x)=x**2"],
            # Constraints to prevent redundant nested functions
            nested_constraints={
                "sin": {"sin": 0, "cos": 0},
                "cos": {"sin": 0, "cos": 0},
                "exp": {"exp": 0},
                "log": {"log": 0},
                "square": {"square": 0},
            },
            
            # Constant optimization
            optimizer_nrestarts=5,
            
            # For reproducibility and clean output
            random_state=42,
            verbosity=0,
            progress=False,
        )

        model.fit(X, y, variable_names=["x1", "x2"])
        
        predictions = None
        complexity = None
        expression = "0"

        if len(model.equations_) > 0:
            best_expr_sympy = model.sympy()
            
            # Replace the custom 'square(x)' operator with 'x**2' to conform
            # to the allowed operators in the problem specification.
            square_func = Function('square')
            wild_arg = Wild('a')
            final_expr_sympy = best_expr_sympy.replace(square_func(wild_arg), wild_arg**2)
            
            expression = str(final_expr_sympy)
            
            predictions = model.predict(X)
            complexity = model.equations_.iloc[-1]['complexity']
            
        else:
            # Fallback to a linear model if PySR fails to find an expression.
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c = coeffs
                expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
                preds_arr = a * x1 + b * x2 + c
                predictions = preds_arr.tolist()
            except np.linalg.LinAlgError:
                expression = "0"
                predictions = np.zeros_like(y).tolist()

        details = {}
        if complexity is not None:
            details["complexity"] = int(complexity)

        return {
            "expression": expression,
            "predictions": predictions.tolist() if isinstance(predictions, np.ndarray) else predictions,
            "details": details
        }
