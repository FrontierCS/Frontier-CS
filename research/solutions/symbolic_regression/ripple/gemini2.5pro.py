import numpy as np
from pysr import PySRRegressor
import sympy

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
        x1, x2 = X[:, 0], X[:, 1]
        
        # Feature engineering: Add r^2 = x1^2 + x2^2 as a feature.
        # This is a strong prior for problems with radial symmetry like ripples.
        r2 = x1**2 + x2**2
        X_engineered = np.c_[X, r2]
        
        # Configure PySRRegressor. Parameters are tuned for this specific problem.
        model = PySRRegressor(
            niterations=60,
            populations=16,
            population_size=40,
            maxsize=30,
            binary_operators=["+", "-", "*", "/", "pow"],
            unary_operators=["sin", "cos"],
            # Align PySR's complexity metric with the competition's scoring metric
            complexity_of_binary_operators=2,
            complexity_of_unary_operators=1,
            complexity_of_constants=1,
            complexity_of_variables=1,
            # Add constraints to prune the search space
            nested_constraints={"sin": {"cos": 0}, "cos": {"sin": 0}},
            # Use all available CPU cores for parallelism
            procs=0,
            random_state=42,
            verbosity=0,
            progress=False,
        )
        
        try:
            model.fit(X_engineered, y, variable_names=["x1", "x2", "r2"])
        except Exception:
            # Fallback if the PySR backend (Julia) fails
            return self._fallback_solve(X, y)

        try:
            # Check if any equations were found
            if not hasattr(model, 'equations_') or model.equations_.shape[0] == 0:
                return self._fallback_solve(X, y)

            sympy_expr_with_r2 = model.sympy()
            
            s_x1, s_x2, s_r2 = sympy.symbols('x1 x2 r2')
            
            # Substitute the engineered feature back to its base form
            final_sympy_expr = sympy_expr_with_r2.subs(s_r2, s_x1**2 + s_x2**2)
            
            expression_str = str(final_sympy_expr)
            
            # Use the fitted model to generate predictions on the engineered features
            predictions = model.predict(X_engineered)
            
            # Extract complexity from the best equation
            best_equation = model.get_best()
            complexity = best_equation.complexity
            details = {"complexity": int(complexity)}

            return {
                "expression": expression_str,
                "predictions": predictions.tolist(),
                "details": details,
            }

        except (AttributeError, IndexError, RuntimeError):
            # Fallback for any other errors during expression retrieval
            return self._fallback_solve(X, y)

    def _fallback_solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Provides a simple linear regression model as a fallback solution.
        """
        x1, x2 = X[:, 0], X[:, 1]
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
        except np.linalg.LinAlgError:
            a, b, c = 0.0, 0.0, np.mean(y) if y.size > 0 else 0.0

        expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
        predictions = a * x1 + b * x2 + c

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {},
        }