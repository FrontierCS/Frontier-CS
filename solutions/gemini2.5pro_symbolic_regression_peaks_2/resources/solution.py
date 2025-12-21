import numpy as np
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        No-op constructor.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the Peaks dataset using PySR.

        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            A dictionary containing the symbolic expression, predictions, and details.
        """

        model = PySRRegressor(
            niterations=200,
            populations=24,
            population_size=50,
            maxsize=40,
            binary_operators=["+", "-", "*", "/", "pow"],
            unary_operators=["sin", "cos", "exp", "log"],
            nested_constraints={
                "exp": {"exp": 0, "log": 0},
                "log": {"exp": 0, "log": 0},
                "sin": {"sin": 0},
                "cos": {"cos": 0},
            },
            procs=8,
            multithreading=True,
            random_state=42,
            verbosity=0,
            progress=False,
            selection_method="tournament",
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2"])
            
            if not model.equations_.shape[0]:
                 # PySR failed to find any equation, return a baseline
                expression = str(np.mean(y))
                predictions = np.full_like(y, np.mean(y))
            else:
                best_expr_sympy = model.sympy()
                expression = str(best_expr_sympy)
                predictions = model.predict(X)

        except (IndexError, KeyError, RuntimeError):
            # Fallback in case of PySR errors or no equations found
            expression = str(np.mean(y))
            predictions = np.full_like(y, np.mean(y))

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
