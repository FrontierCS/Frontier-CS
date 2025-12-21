import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the Symbolic Regression problem for the McCormick dataset.
        """
        variable_names = ["x1", "x2"]
        
        # Subsample dataset if too large to ensure efficient processing
        n_samples = X.shape[0]
        if n_samples > 2000:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_samples, 2000, replace=False)
            X_train = X[indices]
            y_train = y[indices]
        else:
            X_train = X
            y_train = y

        # Configure PySRRegressor
        # The McCormick function is f(x1, x2) = sin(x1 + x2) + (x1 - x2)^2 - 1.5*x1 + 2.5*x2 + 1
        # We enable specific operators to find this form efficiently.
        model = PySRRegressor(
            niterations=60,
            binary_operators=["+", "-", "*", "^"],
            unary_operators=["sin", "cos"],
            populations=20,
            population_size=40,
            maxsize=45,
            verbosity=0,
            progress=False,
            random_state=42,
            multiprocessing=True,
            temp_equation_file=True,
            delete_tempfiles=True,
            timeout_in_seconds=500
        )

        # Fit the model
        model.fit(X_train, y_train, variable_names=variable_names)

        # Select the best equation based on lowest loss (MSE)
        if hasattr(model, 'equations_') and model.equations_ is not None and not model.equations_.empty:
            # Identify the index of the equation with the minimum loss
            best_idx = model.equations_['loss'].idxmin()
            
            # Retrieve the sympy expression object
            best_expr_sympy = model.equations_.loc[best_idx, 'sympy_format']
            
            # Convert to string (PySR/SymPy outputs standard Python operators like **)
            expression = str(best_expr_sympy)
            
            # Compute predictions on the full dataset using the selected equation
            predictions = model.predict(X, index=best_idx)
        else:
            # Fallback linear baseline if symbolic regression fails
            expression = "0.0"
            predictions = np.zeros(n_samples)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
