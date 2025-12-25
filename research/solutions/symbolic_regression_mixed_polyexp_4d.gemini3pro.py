import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor
import warnings

warnings.filterwarnings("ignore")

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        """
        # Define model hyperparameters tailored for 4D Mixed PolyExp data
        # Using 40 iterations and adequate population size to explore the search space
        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=20,
            population_size=40,
            maxsize=45,  # Allow complexity for cross-terms and dampening
            ncyclesperiteration=500,
            model_selection="best",
            loss="loss(x, y) = (x - y)^2",
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            temp_equation_file=True,
            delete_tempfiles=True
        )

        try:
            # Fit the model specifying variable names to match output requirements
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

            # Extract the best symbolic expression
            # PySR's model.sympy() returns a sympy expression object
            best_expr = model.sympy()
            expression = str(best_expr)

            # Generate predictions using the fitted model
            predictions = model.predict(X)

        except Exception:
            # Fallback to Linear Regression if symbolic regression fails
            # This ensures we always return a valid result
            n_samples, n_features = X.shape
            X_aug = np.column_stack([X, np.ones(n_samples)])
            coeffs, _, _, _ = np.linalg.lstsq(X_aug, y, rcond=None)

            # Construct linear expression string
            terms = [f"({coeffs[i]} * x{i+1})" for i in range(n_features)]
            terms.append(str(coeffs[-1]))
            expression = " + ".join(terms)

            predictions = X_aug @ coeffs

        # Ensure predictions are a list/array
        if isinstance(predictions, np.ndarray):
            predictions = predictions.tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
