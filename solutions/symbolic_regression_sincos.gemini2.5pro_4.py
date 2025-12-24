import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        Initializes the PySRRegressor with a configuration optimized for the
        8-core CPU environment and the specifics of the SinCos dataset.
        """
        self.model = PySRRegressor(
            niterations=60,
            populations=16,
            population_size=40,
            procs=8,
            binary_operators=["+", "-", "*", "/", "**"],
            # Strong prior based on dataset name "SinCos"
            unary_operators=["sin", "cos"],
            maxsize=25,
            model_selection="best",
            random_state=42,
            verbosity=0,
            progress=False,
            temp_equation_file=False,
        )

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Fits the PySR model to the data and returns the best symbolic expression.

        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            A dictionary containing the symbolic expression, predictions, and
            details about the model's complexity.
        """
        self.model.fit(X, y, variable_names=["x1", "x2"])

        # Check if PySR found any valid equations
        if not hasattr(self.model, 'equations_') or self.model.equations_.empty:
            # Provide a fallback solution if PySR fails
            expression = "0.0"
            predictions = np.zeros_like(y)
            details = {"complexity": 0}
        else:
            # Get the best symbolic expression found by PySR
            best_expr_sympy = self.model.sympy()
            expression = str(best_expr_sympy)
            
            # Generate predictions using the best model
            predictions = self.model.predict(X)
            
            # Extract complexity from the best model's details
            best_equation_details = self.model.get_best()
            details = {"complexity": int(best_equation_details.complexity)}

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details
        }
