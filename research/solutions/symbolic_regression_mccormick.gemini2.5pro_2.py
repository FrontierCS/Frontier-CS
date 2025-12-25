import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        An expert programmer's solution for symbolic regression.
        This constructor can be used to pass hyperparameters, but for this
        problem, we use a fixed robust configuration.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given dataset using PySR.
        
        The method is configured to find expressions involving trigonometric
        and polynomial terms, which is suitable for the McCormick function.
        It uses a multi-population genetic algorithm search, optimized for a
        multi-core CPU environment.
        """
        # Configure PySRRegressor with parameters suitable for the problem and environment.
        # The number of populations is set to leverage the 8 vCPUs.
        # Iterations and maxsize are increased for a more thorough search.
        # 'pow' is included to easily find squared terms.
        model = PySRRegressor(
            niterations=60,
            populations=16,
            binary_operators=["+", "-", "*", "/", "pow"],
            unary_operators=["sin", "cos"],
            maxsize=30,
            random_state=42,
            verbosity=0,
            progress=False,
            # PySR's default parallelization is efficient on multi-core CPUs.
        )

        model.fit(X, y, variable_names=["x1", "x2"])

        # If PySR fails to find any valid expression, fall back to a
        # simple linear regression model as a baseline.
        if not hasattr(model, 'equations_') or model.equations_.empty:
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c = coeffs
                expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
            except np.linalg.LinAlgError:
                # Ultimate fallback in case of numerical errors.
                expression = "0.0"
            
            return {
                "expression": expression,
                "predictions": None,  # Evaluator will compute predictions
                "details": {}
            }

        # Retrieve the best symbolic expression found by PySR.
        # model.sympy() returns the expression with the best score (accuracy vs. complexity).
        best_sympy_expr = model.sympy()
        expression = str(best_sympy_expr)

        # Generate predictions from the best model.
        # Providing them saves computation time for the evaluation service.
        predictions = model.predict(X)
        
        # Extract the complexity of the best model for scoring.
        # The equations_ dataframe is sorted by score, so the last entry is the best.
        complexity = int(model.equations_.iloc[-1]['complexity'])

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {
                "complexity": complexity
            }
        }
