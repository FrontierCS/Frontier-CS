import numpy as np
from pysr import PySRRegressor
from typing import Dict

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> Dict:
        # Use PySR to find symbolic expression
        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=12,
            population_size=35,
            maxsize=25,
            verbosity=0,
            progress=False,
            random_state=42,
            temp_equation_file=True,
            tempdir="./",
            procs=8,
            multithreading=True,
            loss="L2DistLoss()",
            early_stop_condition=("stop_if(loss, 1e-6)"),
            model_selection="best",
        )
        
        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        
        # Get best expression
        try:
            best_expr = model.sympy()
            expression = str(best_expr)
        except:
            # Fallback to best equation from model
            equations = model.equations_
            best_eq = equations[equations['loss'].idxmin()]
            expression = best_eq['equation']
        
        # Clean up expression
        expression = self._clean_expression(expression)
        
        # Compute predictions
        predictions = self._evaluate_expression(expression, X)
        
        # Compute complexity
        complexity = self._compute_complexity(expression)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }
    
    def _clean_expression(self, expr: str) -> str:
        """Clean and format the expression string."""
        import sympy
        from sympy import sympify
        
        # Remove 'x' prefix if present (PySR sometimes adds it)
        expr = expr.replace('x1', 'x1').replace('x2', 'x2')
        expr = expr.replace('x3', 'x3').replace('x4', 'x4')
        
        # Simplify expression
        try:
            sympy_expr = sympify(expr)
            simplified = sympy.simplify(sympy_expr)
            expr = str(simplified)
        except:
            pass
        
        # Replace double operators and clean up
        expr = expr.replace(' ', '')
        expr = expr.replace('**', '**')
        
        return expr
    
    def _evaluate_expression(self, expr: str, X: np.ndarray) -> np.ndarray:
        """Safely evaluate the expression on input data."""
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]
        
        # Define safe versions of functions
        def safe_log(x):
            return np.log(np.abs(x) + 1e-12)
        
        # Safe evaluation with numpy
        try:
            # Use eval with limited namespace
            namespace = {
                'x1': x1, 'x2': x2, 'x3': x3, 'x4': x4,
                'sin': np.sin, 'cos': np.cos, 'exp': np.exp,
                'log': safe_log, 'np': np
            }
            result = eval(expr, {"__builtins__": {}}, namespace)
            
            # Handle scalar outputs
            if np.isscalar(result):
                result = np.full(len(x1), result)
            
            return np.array(result, dtype=np.float64)
        except:
            # Fallback: return zeros
            return np.zeros(len(x1))
    
    def _compute_complexity(self, expr: str) -> int:
        """Compute expression complexity score."""
        import re
        
        # Count binary operators
        binary_ops = len(re.findall(r'[\+\-\*/]', expr))
        power_ops = expr.count('**')
        binary_count = binary_ops + power_ops
        
        # Count unary functions
        unary_count = 0
        for func in ['sin', 'cos', 'exp', 'log']:
            unary_count += expr.count(func)
        
        # Complexity formula: 2 * binary + unary
        return 2 * binary_count + unary_count