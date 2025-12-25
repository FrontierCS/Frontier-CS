import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        Initialize the solution.
        kwargs are any arguments passed from the evaluation environment.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given dataset.

        Args:
            X: Feature matrix of shape (n, 2).
            y: Target values of shape (n,).

        Returns:
            A dictionary with the symbolic expression, predictions, and details.
        """
        
        # Configure PySRRegressor with parameters tuned for this problem.
        # The dataset name "SinCos" strongly suggests that trigonometric functions
        # are key, so we focus the search on 'sin' and 'cos'.
        model = PySRRegressor(
            niterations=75,          # Number of generations
            populations=48,          # Number of populations running in parallel
            population_size=50,      # Number of expressions per population
            procs=8,                 # Use all available CPU cores
            maxsize=25,              # Maximum complexity of expressions
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos"],
            model_selection="best",  # Selects the best expression based on score (accuracy vs. complexity)
            verbosity=0,
            progress=False,
            random_state=42,
            turbo=True,              # Use JIT compilation for faster evaluation
            parsimony=0.0005,        # Small penalty for complexity, encourages accuracy
            # Prevent redundant nested trigonometric functions like sin(cos(x))
            nested_constraints={"sin": {"cos": 0, "sin": 0}, "cos": {"sin": 0, "cos": 0}},
            # Use standard L2 loss (Mean Squared Error)
            elementwise_loss="L2DistLoss()",
            loss="L2DistLoss()",
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # Fallback in case PySR encounters an unexpected error
            return self._fallback_solve(X, y)

        # Check if PySR found any valid equations
        if not hasattr(model, 'equations_') or model.equations_.shape[0] == 0:
            return self._fallback_solve(X, y)

        # Retrieve the best equation found by PySR
        best_equation = model.get_best()
        
        # Get the symbolic expression as a string
        # model.sympy() returns a sympy object, which we convert to a string
        expression_str = str(model.sympy())
        
        # Generate predictions using the best model
        predictions = model.predict(X)

        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": {"complexity": int(best_equation['complexity'])}
        }

    def _fallback_solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        A robust fallback solver using linear least squares with trigonometric features.
        This is a much stronger baseline for a 'SinCos' dataset than a simple linear model.
        """
        x1, x2 = X[:, 0], X[:, 1]
        
        # Create a design matrix with trigonometric and linear features
        A = np.column_stack([np.sin(x1), np.cos(x2), np.cos(x1), np.sin(x2), 
                             x1, x2, np.ones_like(x1)])
        
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c, d, e, f, g = coeffs
            expression = (
                f"{a:.6f}*sin(x1) + {b:.6f}*cos(x2) + {c:.6f}*cos(x1) + {d:.6f}*sin(x2) + "
                f"{e:.6f}*x1 + {f:.6f}*x2 + {g:.6f}"
            )
        except np.linalg.LinAlgError:
            # If the trigonometric fallback fails, revert to a simple linear model
            A_simple = np.column_stack([x1, x2, np.ones_like(x1)])
            try:
                coeffs_simple, _, _, _ = np.linalg.lstsq(A_simple, y, rcond=None)
                a_s, b_s, c_s = coeffs_simple
                expression = f"{a_s:.6f}*x1 + {b_s:.6f}*x2 + {c_s:.6f}"
            except np.linalg.LinAlgError:
                # Ultimate fallback if all else fails
                expression = "0.0"
        
        return {"expression": expression}
