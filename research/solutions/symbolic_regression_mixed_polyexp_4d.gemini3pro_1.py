import numpy as np
from pysr import PySRRegressor
import sympy
import warnings

# Suppress warnings to keep output clean
warnings.filterwarnings("ignore")

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        Falls back to linear regression if symbolic regression fails.
        """
        # 1. Data Preprocessing
        # Subsample if the dataset is too large to ensure we fit within the time limits of the environment
        n_samples = X.shape[0]
        if n_samples > 2000:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_samples, 2000, replace=False)
            X_train = X[indices]
            y_train = y[indices]
        else:
            X_train = X
            y_train = y

        # 2. Configure PySRRegressor
        # Optimized for "Mixed PolyExp 4D": polynomials + exponential decay
        # High likelihood of structure like P(x) * exp(Q(x))
        model = PySRRegressor(
            niterations=100,               # Reasonable balance for 8 vCPUs
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "sin", "cos", "log"],
            populations=20,               # Parallel populations
            population_size=33,
            maxsize=40,                   # Allow enough complexity for 4D interactions
            parsimony=0.001,              # Penalty for complexity
            model_selection="best",       # Select model with best score/complexity trade-off
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,                      # Utilize available vCPUs
            deterministic=True,
            # Constrain nesting to improve search efficiency for this problem type
            # We avoid nested transcendental functions (e.g., sin(cos(x))) which are rare in PolyExp data
            nested_constraints={
                "exp": {"exp": 0, "sin": 0, "cos": 0, "log": 0},
                "sin": {"exp": 0, "sin": 0, "cos": 0, "log": 0},
                "cos": {"exp": 0, "sin": 0, "cos": 0, "log": 0},
                "log": {"exp": 0, "sin": 0, "cos": 0, "log": 0},
            },
        )

        expression = ""
        predictions = None

        try:
            # 3. Fit Model
            model.fit(X_train, y_train, variable_names=["x1", "x2", "x3", "x4"])

            # 4. Extract Expression
            # Get the best expression as a sympy object
            best_expr = model.sympy()
            expression = str(best_expr)

            # 5. Generate Predictions
            # Predict on the full original dataset
            predictions = model.predict(X)

            # Check for validity
            if np.any(np.isnan(predictions)) or np.any(np.isinf(predictions)):
                raise ValueError("Symbolic model produced invalid predictions.")

        except Exception:
            # 6. Fallback: Linear Regression
            # Used if PySR fails (e.g. timeout, memory, or installation issues)
            # or if predictions are unstable.
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
            # Design matrix with intercept
            A = np.column_stack([x1, x2, x3, x4, np.ones_like(x1)])
            # Least squares solution
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c, d, e = coeffs
            
            expression = f"{a}*x1 + {b}*x2 + {c}*x3 + {d}*x4 + {e}"
            predictions = A @ coeffs

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
