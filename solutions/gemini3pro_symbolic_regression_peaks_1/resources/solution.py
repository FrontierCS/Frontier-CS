import numpy as np
from pysr import PySRRegressor
import sympy
import warnings

# Suppress potential warnings from libraries
warnings.filterwarnings("ignore")

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the Peaks dataset.
        """
        # Subsample data if dataset is too large to ensure performance
        n_samples = X.shape[0]
        max_train_samples = 3000
        
        if n_samples > max_train_samples:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_samples, max_train_samples, replace=False)
            X_train = X[indices]
            y_train = y[indices]
        else:
            X_train = X
            y_train = y

        # Configure PySRRegressor
        # Optimized for 8 vCPUs (procs=8) and the complexity of the Peaks function
        model = PySRRegressor(
            niterations=1000,               # Let timeout_in_seconds control termination
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=16,                 # 2 populations per CPU core
            population_size=50,             # Sufficient diversity
            maxsize=50,                     # Allow complex expressions (Peaks function is complex)
            timeout_in_seconds=300,         # 5 minutes maximum runtime
            model_selection="best",         # Selects best model on the pareto frontier
            procs=8,                        # Use all 8 vCPUs
            multiprocessing=True,
            verbosity=0,                    # Silent mode
            progress=False,
            random_state=42,
            temp_equation_file=True         # Prevent creating permanent files
        )

        # Fit the symbolic regression model
        # variable_names ensures the output expression uses x1, x2
        model.fit(X_train, y_train, variable_names=["x1", "x2"])

        # Retrieve the best expression found
        try:
            sympy_expr = model.sympy()
            expression = str(sympy_expr)
        except Exception:
            # Fallback if no valid expression found (unlikely)
            expression = "x1 * 0"

        # Generate predictions on the full dataset
        try:
            predictions = model.predict(X)
        except Exception:
            # Fallback predictions
            predictions = np.zeros(n_samples)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
