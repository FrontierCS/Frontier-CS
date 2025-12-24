import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Fits a symbolic expression to the given data using PySR.

        The hyperparameters are tuned for the "Peaks" dataset, which is known
        to involve complex interactions between polynomial and exponential terms.
        """
        model = PySRRegressor(
            # Search parameters: A more intensive search for the complex target.
            niterations=60,
            populations=24,
            population_size=40,

            # Environment: Utilize all 8 vCPUs available.
            procs=8,

            # Operators: Focused set based on the problem description.
            # 'pow' is crucial for polynomial terms, 'exp' for the peaks.
            # 'cos' is included to capture potential periodic components.
            binary_operators=["+", "-", "*", "pow"],
            unary_operators=["exp", "cos"],

            # Complexity control: Allow for reasonably complex expressions
            # and adjust parsimony to favor accuracy for this complex problem.
            maxsize=35,
            parsimony=0.001,

            # For reproducibility and clean execution.
            random_state=42,
            verbosity=0,
            progress=False,
        )

        model.fit(X, y, variable_names=["x1", "x2"])

        # Fallback in case PySR fails to find any equations.
        if not hasattr(model, 'equations_') or model.equations_.empty:
            expression = "0.0"
            predictions = np.zeros_like(y)
        else:
            # Select the best equation found by PySR.
            best_expr_sympy = model.sympy()
            expression = str(best_expr_sympy)
            
            # Use the model's predict method for reliable predictions.
            predictions = model.predict(X)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
