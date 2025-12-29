import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        No specific initialization needed for this solution.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the SinCos dataset using PySR.
        
        This solution uses PySR, a genetic programming-based symbolic regression
        library, to find the underlying mathematical expression in the data.
        The hyperparameters are tuned based on the problem description ("SinCos"
        dataset with periodic behavior) and the evaluation environment (8 vCPUs).

        Key tuning decisions:
        - Operator set is focused on `sin`, `cos`, `+`, `*`, `-` to leverage
          problem-specific knowledge and reduce the search space.
        - `niterations`, `populations`, and `population_size` are increased
          from the baseline example to allow for a more thorough search.
        - `procs` is set to 8 to fully utilize the available CPU cores.
        - `complexity_of_operators` is configured to match the problem's
          scoring formula, guiding PySR's internal selection towards
          expressions that will score higher.
        - A fallback mechanism is implemented to handle the case where PySR
          does not find any valid expressions.
        """
        model = PySRRegressor(
            niterations=100,
            populations=24,
            population_size=50,
            procs=8,
            binary_operators=["+", "*", "-"],
            unary_operators=["sin", "cos"],
            maxsize=20,
            random_state=42,
            verbosity=0,
            progress=False,
            temp_equation_file=True,
            complexity_of_operators={
                "+": 2, "*": 2, "-": 2,
                "sin": 1, "cos": 1
            },
        )

        model.fit(X, y, variable_names=["x1", "x2"])

        if len(model.equations) == 0:
            # Fallback if no expression is found by PySR
            mean_y = np.mean(y)
            expression = f"{mean_y:.8f}"
            predictions = np.full_like(y, mean_y)
        else:
            # Get the best expression and its predictions
            expression = str(model.sympy())
            predictions = model.predict(X)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }