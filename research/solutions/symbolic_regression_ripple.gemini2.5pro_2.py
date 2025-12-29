import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def _sympy_to_str(self, expr: sympy.Expr) -> str:
        """
        Converts a sympy expression to a Python-evaluable string,
        ensuring no disallowed functions (like 'sqrt') are present.
        """
        # Replace all instances of sqrt(x) with Pow(x, 0.5) to use the allowed '**' operator.
        replacements = {e: sympy.Pow(e.args[0], 0.5) for e in expr.atoms(sympy.sqrt)}
        expr_no_sqrt = expr.xreplace(replacements)
        
        # Use sympy.sstr for a machine-readable, Python-compatible output with full precision.
        return sympy.sstr(expr_no_sqrt, full_prec=True)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the ripple dataset.
        """
        # Configure PySRRegressor with parameters tuned for the ripple dataset and environment.
        # The "ripple" nature suggests trigonometric functions are important.
        model = PySRRegressor(
            niterations=200,
            populations=24,
            population_size=40,
            binary_operators=["+", "-", "*", "/", "pow"],
            unary_operators=["sin", "cos"], # Focus on trigonometric functions.
            maxsize=35,
            procs=8, # Utilize all 8 vCPUs.
            temp_equation_file=True,
            complexity_of_operators={"sin": 2, "cos": 2},
            random_state=42, # For reproducibility.
            verbosity=0,
            progress=False,
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2"])
            
            # Check if PySR found any valid equations.
            if not hasattr(model, 'equations_') or model.equations_.empty:
                # Fallback if no solution is found.
                expression = "0.0"
                predictions = np.zeros_like(y)
                complexity = 0
            else:
                # Retrieve the best expression and its properties.
                best_expr_sympy = model.sympy()
                expression = self._sympy_to_str(best_expr_sympy)
                predictions = model.predict(X)
                complexity = int(model.equations_.iloc[-1]['complexity'])

        except Exception:
            # General fallback in case of any runtime error from PySR.
            expression = "0.0"
            predictions = np.zeros_like(y)
            complexity = 0

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {
                "complexity": complexity
            }
        }