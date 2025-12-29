import numpy as np
import sympy as sp
from pysr import PySRRegressor

class Solution:
    """
    A solution for symbolic regression on the McCormick dataset using PySR.
    """
    def __init__(self, **kwargs):
        """
        Initialize the solution.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data using PySR.

        Args:
            X: Feature matrix of shape (n, 2) with columns x1, x2.
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the symbolic expression, predictions, and details.
        """
        # The evaluation environment has 8 vCPUs. We'll use all of them.
        n_procs = 8

        # Configure the PySRRegressor.
        # Parameters are chosen to balance search time and solution quality,
        # tailored for the McCormick function's known structure (trigonometric and polynomial).
        model = PySRRegressor(
            # --- Search Configuration ---
            niterations=50,
            populations=16,      # A good number for 8 cores (2 per core)
            population_size=33,  # PySR's default, generally works well
            maxsize=25,          # True function complexity is ~17, this gives some margin

            # --- Operators ---
            # The true function uses +, -, *, **, sin. We add cos as it's related.
            # Division is excluded as it's not present in the true function and can
            # slow down search or cause instability.
            binary_operators=["+", "-", "*", "**"],
            unary_operators=["sin", "cos"],

            # --- Complexity vs Accuracy Trade-off ---
            # A slightly higher parsimony value encourages simpler expressions,
            # which aligns with the scoring formula's preference for low complexity.
            parsimony=0.005,

            # --- Constant Optimization ---
            # BFGS is a robust optimizer for tuning constants in expressions.
            # More restarts can help find better constants.
            optimizer_algorithm="BFGS",
            optimizer_nrestarts=3,

            # --- Environment & Reproducibility ---
            procs=n_procs,
            random_state=42,

            # --- Output Control ---
            verbosity=0,
            progress=False,
        )

        # Run the symbolic regression search
        model.fit(X, y, variable_names=["x1", "x2"])

        # Check if the search was successful and found any equations
        if not hasattr(model, 'equations_') or model.equations_.empty:
            # Fallback if PySR fails to find any valid expressions.
            # Return a simple constant expression.
            expression = "0.0"
            # Predictions will be computed by the evaluator from the expression.
            predictions = np.zeros_like(y).tolist()
            complexity = 0
        else:
            # Retrieve the best expression found by PySR.
            # model.sympy() returns the best equation in sympy format.
            sympy_expr = model.sympy()

            # Simplify the expression for better readability and potentially
            # a better complexity score if simplification reduces operations.
            try:
                simplified_expr = sp.simplify(sympy_expr)
            except (TypeError, AttributeError, RecursionError):
                # Fallback to the original expression if simplification fails
                simplified_expr = sympy_expr
            
            expression = str(simplified_expr)

            # Generate predictions from the final model. Providing them is optional
            # but ensures they match PySR's internal evaluation.
            predictions = model.predict(X).tolist()

            # Get the complexity of the final model for the details dictionary.
            complexity = model.get_best()['complexity']

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {"complexity": int(complexity)}
        }