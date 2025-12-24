import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        """
        Initializes the Solution class.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data.

        Args:
            X: Feature matrix of shape (n, 2).
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the symbolic expression and predictions.
        """
        # Configure PySRRegressor. The parameters are tuned for the Ripple dataset,
        # which is known to have a structure of (polynomial) * sin(polynomial).
        # We constrain the search space to operators that can form such expressions.
        model = PySRRegressor(
            niterations=80,
            populations=24,
            population_size=35,
            
            # Operators are chosen to match the expected structure of the target function.
            # x**2 can be formed by x*x. This focuses the search.
            binary_operators=["+", "-", "*"],
            unary_operators=["sin", "cos"],
            
            maxsize=30,  # A complexity limit to prevent overfitting.
            
            # Annealing can help the search escape local optima.
            annealing=True,
            
            # Use all available CPU cores.
            procs=8,
            
            # For reproducibility.
            random_state=42,
            
            # Suppress console output.
            verbosity=0,
            progress=False,
            
            # Using a temporary file for equations is safer in parallel environments.
            temp_equation_file=True,
        )

        model_fitted_successfully = False
        try:
            # Fit the model to the data.
            model.fit(X, y, variable_names=["x1", "x2"])
            if hasattr(model, 'equations_') and not model.equations_.empty:
                model_fitted_successfully = True
        except Exception:
            # PySR can encounter errors, especially with its Julia backend.
            # We catch them to allow the fallback mechanism to run.
            pass

        # Fallback mechanism if PySR fails or finds no valid equations.
        if not model_fitted_successfully:
            # A simple linear model serves as a robust fallback.
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c = coeffs
                expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
                predictions = a * x1 + b * x2 + c
                status = "pysr_failed_fallback_linear"
            except np.linalg.LinAlgError:
                # If linear regression also fails, fallback to the mean.
                mean_y = np.mean(y)
                expression = f"{mean_y:.6f}"
                predictions = np.full_like(y, mean_y)
                status = "pysr_and_linear_failed_fallback_mean"
            
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"status": status}
            }

        # Extract the best symbolic expression found by PySR.
        best_sympy_expr = model.sympy()
        
        # Convert the sympy expression to a standard Python string.
        expression_str = str(best_sympy_expr)
        
        # Generate predictions using the best found model.
        predictions = model.predict(X)

        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": {}
        }
