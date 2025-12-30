import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        """
        Initializes the Solution class.
        Any provided keyword arguments are ignored.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given dataset using PySR.

        Args:
            X: Feature matrix of shape (n, 2) with columns 'x1', 'x2'.
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the symbolic expression, predictions, and details.
        """
        # Configure the PySR regressor. The parameters are tuned for the "Peaks"
        # dataset, which is expected to have exponential and polynomial features.
        # The configuration leverages the available 8 vCPUs.
        model = PySRRegressor(
            procs=8,
            populations=32,
            population_size=40,
            niterations=100,
            # Operators allowed by the problem specification. 'pow' corresponds to '**'.
            binary_operators=["+", "-", "*", "/", "pow"],
            # Unary functions allowed. 'exp' is crucial for a peaks-like function.
            # 'log' is included as it is allowed, PySR protects it against non-positive inputs.
            unary_operators=["exp", "cos", "sin", "log"],
            # Allow for reasonably complex expressions to capture the peaks.
            maxsize=35,
            # Use a small crossover probability to introduce new genetic material.
            crossover_probability=0.05,
            # Annealing helps the search to favor simpler, more accurate expressions.
            annealing=True,
            # Manage temporary files automatically.
            temp_equation_file=True,
            # Set a random state for reproducibility of the search process.
            random_state=42,
            # Suppress verbose output during execution.
            verbosity=0,
            progress=False,
            # A timeout to ensure the process completes within a reasonable time frame.
            timeout_in_seconds=600
        )

        try:
            # Run the symbolic regression search.
            # Variable names are provided to ensure the output expression uses 'x1' and 'x2'.
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # Fallback to mean if PySR fails catastrophically.
            mean_y = np.mean(y)
            expression = f"{mean_y:.8f}"
            return {
                "expression": expression,
                "predictions": np.full_like(y, mean_y).tolist(),
                "details": {"fallback": "pysr_fit_exception"}
            }

        # If the search completes but finds no valid equations, provide a fallback.
        if not hasattr(model, 'equations_') or model.equations_.empty:
            mean_y = np.mean(y)
            expression = f"{mean_y:.8f}"
            return {
                "expression": expression,
                "predictions": np.full_like(y, mean_y).tolist(),
                "details": {"fallback": "no_equations_found"}
            }

        # Extract the best symbolic expression. model.sympy() returns it as a SymPy object.
        best_expr_sympy = model.sympy()
        
        # Convert the SymPy expression to a Python-evaluable string.
        # str() handles conversion of Pow to **, etc.
        expression = str(best_expr_sympy)

        # Generate predictions using the best-found model.
        predictions = model.predict(X)

        # Extract the complexity of the best model from the results dataframe.
        try:
            best_idx = model.equations_.score.idxmax()
            complexity = int(model.equations_.loc[best_idx, 'complexity'])
            details = {"complexity": complexity}
        except (ValueError, KeyError):
            # Fallback if score or complexity cannot be determined.
            details = {}

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details,
        }