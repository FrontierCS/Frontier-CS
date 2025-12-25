import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        """
        Initialize the Solution class.
        The main logic is contained within the solve method.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression that fits the given data using PySR.
        """
        # Configure the PySR regressor. Parameters are set for a thorough search
        # suitable for the complexity of the "Peaks" dataset.
        model = PySRRegressor(
            niterations=100,
            populations=20,
            population_size=40,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            maxsize=35,
            procs=8,
            random_state=42,
            verbosity=0,
            progress=False,
            optimizer_nrestarts=2,
            model_selection="best",
        )

        # Fit the model to the data, specifying variable names for the expression.
        model.fit(X, y, variable_names=["x1", "x2"])

        # Check if PySR found any equations and handle the result.
        if not hasattr(model, 'equations_') or model.equations_.shape[0] == 0:
            # Fallback if no solution is found
            expression = "0.0"
            predictions = np.zeros_like(y)
            complexity = 0
        else:
            # Extract the best equation's details.
            best_equation_info = model.get_best()
            
            # Get the symbolic expression via sympy for correct formatting.
            best_expr_sympy = model.sympy()
            expression = str(best_expr_sympy)
            
            complexity = best_equation_info.get('complexity', 0)
            
            # Generate predictions using the fitted model.
            predictions = model.predict(X)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": int(complexity)},
        }
