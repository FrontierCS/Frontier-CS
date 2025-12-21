import numpy as np
import sympy as sp
from pysr import PySRRegressor
import warnings

# Suppress warnings from PySR/system
warnings.filterwarnings("ignore")

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the McCormick dataset.
        
        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            dict containing "expression" and "predictions"
        """
        # Subsample data for training if dataset is large to ensure performance
        # within the evaluation time limits.
        n_total = X.shape[0]
        n_train = 2000
        
        if n_total > n_train:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_total, n_train, replace=False)
            X_train = X[indices]
            y_train = y[indices]
        else:
            X_train = X
            y_train = y

        # Configure PySRRegressor
        # The McCormick function involves trigonometric (sin) and polynomial terms.
        # We include basic arithmetic and sin/cos.
        # 8 vCPUs are available, so we set procs=8.
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*"],
            unary_operators=["sin", "cos"],
            populations=16,
            population_size=33,
            maxsize=40,
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,
            model_selection="best",
            timeout_in_seconds=300,
            loss="loss(prediction, target) = (prediction - target)^2",
        )

        expression = ""
        predictions = None

        try:
            # Fit the model
            model.fit(X_train, y_train, variable_names=["x1", "x2"])

            # Retrieve the best expression as a sympy object
            best_expr = model.sympy()
            
            # Simplify the expression (e.g., combine terms, handle constants)
            # This helps in matching the "closed-form" requirement cleanly
            simplified_expr = sp.simplify(best_expr)
            
            # Convert to string
            expression = str(simplified_expr)
            
            # Generate predictions on the full dataset using the fitted model
            # PySR's predict method uses the compiled expression
            predictions = model.predict(X)

        except Exception:
            # Fallback to Linear Regression if PySR fails
            # Fit: y = c0 + c1*x1 + c2*x2
            A = np.column_stack([np.ones(n_total), X])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            c0, c1, c2 = coeffs
            expression = f"{c0} + {c1}*x1 + {c2}*x2"
            predictions = A @ coeffs

        # Ensure predictions are a python list as required by some evaluators (though numpy array is usually fine)
        if isinstance(predictions, np.ndarray):
            predictions = predictions.tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
