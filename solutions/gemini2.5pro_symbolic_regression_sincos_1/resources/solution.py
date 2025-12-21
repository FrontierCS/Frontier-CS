import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        """
        The constructor is not used in this solution.
        The PySR model is initialized within the solve method.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data using PySR.

        Args:
            X: Feature matrix of shape (n, 2).
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the symbolic expression, predictions, and complexity.
        """
        # Initialize the PySR regressor with a configuration tuned for this problem.
        # The parameters are chosen based on:
        # - The problem name "SinCos", hinting at trigonometric functions.
        # - The scoring formula's complexity definition.
        # - The evaluation environment's 8 vCPUs.
        model = PySRRegressor(
            # Search configuration: a more thorough search than the default.
            niterations=100,
            populations=40,
            population_size=50,

            # Operators: focus on trigonometric functions as hinted by the problem name.
            unary_operators=["sin", "cos"],
            binary_operators=["+", "-", "*", "/"],

            # Align PySR's complexity calculation with the competition's scoring formula:
            # Score C = 2 * (#binary ops) + (#unary ops)
            complexity_of_unary_operators=1,
            complexity_of_binary_operators=2,
            
            # Constraints to guide the search towards simpler, more plausible expressions.
            maxsize=30,  # Limit expression complexity.
            # Prevent redundant nested trigonometric functions like sin(sin(x)).
            nested_constraints={"sin": {"sin": 0, "cos": 0}, "cos": {"sin": 0, "cos": 0}},

            # Early stopping for efficiency: stop if a very good solution is found.
            early_stop_condition="f(loss, complexity) < 1e-8",
            
            # Performance: procs defaults to cpu_count(), which is optimal for the environment.
            # We also add a timeout as a safeguard.
            timeout_in_seconds=600,

            # Reproducibility and I/O
            random_state=42,
            verbosity=0,
            progress=False,
        )

        model.fit(X, y, variable_names=["x1", "x2"])

        # After fitting, extract the results.
        if len(model.equations_) == 0:
            # Fallback in case PySR fails to find any valid expression.
            expression = "0.0"
            predictions = np.zeros_like(y)
            complexity = 0
        else:
            # Get the best expression (selected by PySR based on its score).
            best_expr_sympy = model.sympy()
            expression = str(best_expr_sympy)

            # Generate predictions using the best found model.
            predictions = model.predict(X)
            
            # Get the complexity of the best equation.
            # The model is configured to calculate complexity as required by the problem.
            best_equation_idx = model.equations_['score'].idxmax()
            complexity = model.equations_.loc[best_equation_idx, 'complexity']

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {
                "complexity": int(complexity)
            }
        }
