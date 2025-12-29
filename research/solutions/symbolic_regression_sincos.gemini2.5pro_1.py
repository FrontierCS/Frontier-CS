import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        Initialize the PySR regressor with hyperparameters tuned for the environment.
        """
        self.model = PySRRegressor(
            # Search configuration: An aggressive search for better solutions.
            niterations=80,
            populations=32,
            population_size=50,
            
            # Environment configuration: Utilize all available CPU cores.
            procs=8,
            
            # Expression constraints to guide the search towards simpler solutions.
            maxsize=20,
            binary_operators=["+", "-", "*", "/", "pow"],
            
            # Heuristic based on the dataset name "SinCos": focus on trigonometric functions.
            # This prunes the search space, allowing a deeper search with relevant operators.
            unary_operators=["sin", "cos"],
            
            # Other settings for a robust and reproducible run.
            model_selection="best",  # Balances accuracy and complexity, aligning with the scoring.
            random_state=42,         # For reproducibility.
            verbosity=0,             # Suppress console output.
            progress=False,          # Suppress progress bar.
        )

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data using PySR.

        Args:
            X: Feature matrix of shape (n, 2).
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the symbolic expression, predictions, and details.
        """
        # Use a try-except block for robustness, as PySR can sometimes fail.
        try:
            self.model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # Provide a fallback solution if PySR encounters an error during fitting.
            return {
                "expression": "0.0",
                "predictions": np.zeros_like(y).tolist(),
                "details": {}
            }

        # Check if the model successfully found any equations.
        if not hasattr(self.model, 'equations_') or self.model.equations_.empty:
            # This can happen if the search times out or finds no valid expressions.
            expression = "0.0"
            predictions = np.zeros_like(y)
            details = {}
        else:
            # Extract the best solution from the fitted model.
            best_expr_sympy = self.model.sympy()
            expression = str(best_expr_sympy)

            # Generate predictions from the best expression.
            predictions = self.model.predict(X)

            # Get complexity from the results dataframe for inclusion in details.
            best_eq_details = self.model.equations_.iloc[self.model.equation_]
            complexity = int(best_eq_details['complexity'])
            details = {"complexity": complexity}

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details
        }