import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        The `kwargs` argument is for compatibility with the evaluation environment.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Learns a symbolic expression for the given data using PySR.

        Args:
            X: Feature matrix of shape (n, 2) with columns 'x1', 'x2'.
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the symbolic expression, predictions, and details.
        """
        # Configure PySRRegressor. The parameters are chosen to balance search
        # thoroughness with the computational constraints of the environment.
        # The McCormick function's structure (trigonometric and polynomial terms)
        # guides the choice of operators.
        model = PySRRegressor(
            # Search and evolution parameters
            niterations=60,       # Number of generations for evolution
            populations=32,         # Number of parallel populations (good for multicore)
            population_size=40,     # Size of each population

            # Operators to build expressions from
            binary_operators=["+", "-", "*", "**"],
            unary_operators=["sin", "cos"],

            # Constraints to guide the search towards simpler, more plausible models
            maxsize=30,             # Maximum complexity of an expression tree
            nested_constraints={"sin": 1, "cos": 1}, # Limits nesting of trig funcs

            # Loss and model selection strategy
            model_selection="best", # Selects the model with the best score (accuracy vs. complexity)

            # Environment and performance settings
            procs=0,                # Use all available CPU cores
            random_state=42,        # Ensure reproducibility

            # Suppress verbose output
            verbosity=0,
            progress=False,
        )

        # Run the symbolic regression search
        model.fit(X, y, variable_names=["x1", "x2"])

        # Process the results
        # A fallback is included in case PySR fails to find any valid equations.
        if not hasattr(model, 'equations_') or model.equations_.empty:
            expression = "0.0"  # A safe, neutral expression
            predictions = np.zeros_like(y)
            details = {}
        else:
            # Retrieve the best expression found
            best_sympy_expr = model.sympy()
            expression = str(best_sympy_expr)

            # Generate predictions using the internal model
            predictions = model.predict(X)
            
            # Extract complexity for the details dictionary
            best_equation_details = model.get_best()
            complexity = best_equation_details.get("complexity")
            details = {"complexity": int(complexity)} if complexity is not None else {}

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details,
        }
