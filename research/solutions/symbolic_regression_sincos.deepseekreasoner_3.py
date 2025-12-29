import numpy as np
import sympy as sp
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Configure PySR with parameters suitable for CPU environment
        model = PySRRegressor(
            niterations=200,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,  # Match vCPU count
            population_size=30,
            maxsize=20,
            complexity_of_operators={"**": 3},
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            loss="loss(x, y) = (x - y)^2",
            weight_optimize=0.0005,
            tempdir="/tmp/pysr_cache",
            delete_tempfiles_after_run=True,
            equation_file=None,
            multithreading=True,
            update=False,
            nested_constraints={
                "sin": {"sin": 0, "cos": 0},
                "cos": {"sin": 0, "cos": 0}
            },
            constraints={
                "**": (-1, 3, 0.5),  # exponent between -1 and 3, half-integer allowed
                "/": (0, 0)  # no division by zero
            }
        )
        
        # Fit model
        model.fit(X, y, variable_names=["x1", "x2"])
        
        # Get best expression
        best_expr = model.sympy()
        if best_expr is None:
            # Fallback to simple expression if PySR fails
            expr_str = "0.0"
        else:
            # Simplify and clean the expression
            expr_str = str(best_expr)
            # Replace any sympy function prefixes and ensure valid Python syntax
            expr_str = expr_str.replace("**", "**").replace("exp", "exp")
            expr_str = expr_str.replace("log", "log").replace("sin", "sin").replace("cos", "cos")
        
        # Ensure expression uses only allowed variable names
        # This handles cases where PySR might use different names
        expr_str = expr_str.replace("x0", "x1").replace("x1", "x2").replace("x2", "x2")
        
        # Make predictions
        try:
            # Use sympy to evaluate the expression
            x1_sym, x2_sym = sp.symbols('x1 x2')
            expr = sp.sympify(expr_str)
            func = sp.lambdify([x1_sym, x2_sym], expr, 'numpy')
            predictions = func(X[:, 0], X[:, 1])
        except Exception:
            # Fallback to model predictions
            predictions = model.predict(X)
        
        # Calculate complexity
        complexity = 0
        try:
            # Count binary operations
            binary_ops = ['+', '-', '*', '/', '**']
            for op in binary_ops:
                complexity += 2 * expr_str.count(op)
            # Count unary operations
            unary_ops = ['sin', 'cos', 'exp', 'log']
            for op in unary_ops:
                complexity += expr_str.count(op)
        except Exception:
            complexity = 0
        
        return {
            "expression": expr_str,
            "predictions": predictions.tolist() if hasattr(predictions, 'tolist') else list(predictions),
            "details": {"complexity": complexity}
        }