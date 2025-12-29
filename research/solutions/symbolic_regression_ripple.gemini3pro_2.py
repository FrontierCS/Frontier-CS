import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the Ripple dataset using PySR.
        """
        # Configure PySRRegressor
        # Using 8 vCPUs (procs=8) and appropriate population settings for exploration
        # The Ripple dataset implies trigonometric complexities, so maxsize is increased
        model = PySRRegressor(
            niterations=200,            # High iteration count for convergence
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            maxsize=45,                 # Allow complex expressions for ripple patterns
            populations=24,             # Parallel populations (approx 3 per core)
            population_size=40,
            ncycles_per_iteration=500,
            model_selection="best",     # optimize for accuracy/complexity trade-off
            procs=8,                    # Use all available vCPUs
            multiprocessing=True,
            verbosity=0,
            progress=False,
            random_state=42,
            timeout_in_seconds=600,     # Safety timeout
            temp_equation_file=None,
            delete_tempfiles=True,
        )

        # Fit the model to the data
        # variable_names ensures the output expression uses x1, x2
        model.fit(X, y, variable_names=["x1", "x2"])

        # Extract the best expression found
        try:
            best_expr = model.sympy()
            expression = str(best_expr)
        except Exception:
            # Fallback if no valid expression found (should not happen with default settings)
            expression = "0.0"

        # Generate predictions
        try:
            predictions = model.predict(X)
        except Exception:
            predictions = np.zeros(len(y))

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }