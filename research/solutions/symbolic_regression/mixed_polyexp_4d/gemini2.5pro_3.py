import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        """
        Initialize the solution.
        """
        # PySR model parameters tuned for the 4D problem and CPU environment
        self.model_params = {
            'niterations': 120,
            'populations': 24,
            'population_size': 50,
            'maxsize': 35,
            'binary_operators': ["+", "-", "*", "/"],
            'unary_operators': ["exp", "cos", "sin", "log"],
            'procs': 8,
            'random_state': 42,
            'verbosity': 0,
            'progress': False,
            'loss': "L2DistLoss()",
            'model_selection': "best",
            'timeout_in_seconds': 580, # Generous timeout for a 4D problem
        }
        self.model = PySRRegressor(**self.model_params)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Find a symbolic expression for the given data.

        Args:
            X: Feature matrix of shape (n, 4)
            y: Target values of shape (n,)

        Returns:
            dict with keys:
              - "expression": str, a Python-evaluable expression using x1, x2, x3, x4
              - "predictions": list/array of length n (optional)
              - "details": dict with optional "complexity" int
        """
        variable_names = ["x1", "x2", "x3", "x4"]
        
        try:
            self.model.fit(X, y, variable_names=variable_names)
        except Exception as e:
            # Catch potential errors during PySR execution
            return self._fallback_solution(X, y)

        if not hasattr(self.model, 'equations_') or len(self.model.equations_) == 0:
            # Fallback if PySR finds no equations
            return self._fallback_solution(X, y)

        # Get the best expression
        best_expression_sympy = self.model.sympy()
        expression_str = self._sympy_to_str(best_expression_sympy)
        
        # Get predictions from the best model
        predictions = self.model.predict(X)

        # Get complexity from the final equation
        try:
            # The last equation in the DataFrame is the one selected by `model_selection`
            complexity = int(self.model.equations_.iloc[-1]['complexity'])
        except (KeyError, IndexError):
            complexity = None
        
        details = {}
        if complexity is not None:
            details["complexity"] = complexity

        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": details
        }

    def _fallback_solution(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        A simple linear regression model as a fallback.
        """
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        
        # Design matrix with an intercept term
        A = np.c_[x1, x2, x3, x4, np.ones_like(x1)]
        
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c, d, e = coeffs
            expression = f"{a:.8f}*x1 + {b:.8f}*x2 + {c:.8f}*x3 + {d:.8f}*x4 + {e:.8f}"
            predictions = a * x1 + b * x2 + c * x3 + d * x4 + e
        except np.linalg.LinAlgError:
            # Extremely unlikely, but safe to handle
            expression = "0.0"
            predictions = np.zeros_like(y)
            
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"fallback": True}
        }

    def _sympy_to_str(self, expr: sympy.Expr) -> str:
        """
        Convert a sympy expression to a string that can be evaluated by Python,
        ensuring high precision for floating point numbers.
        """
        # Using sympy.pycode is more robust for python-compatible output
        # but str() is usually sufficient and requested by the prompt's context
        # Let's create a custom printer for high precision
        from sympy.printing.str import StrPrinter

        class HighPrecisionPrinter(StrPrinter):
            def _print_Float(self, expr):
                return f"{expr:.15f}"

        printer = HighPrecisionPrinter()
        return printer.doprint(expr)