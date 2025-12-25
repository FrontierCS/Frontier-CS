import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression that fits the given data using PySR.

        The Ripple Dataset is described as having polynomial amplitude modulation
        with high-frequency trigonometric oscillations, suggesting a function
        with radial symmetry involving sin/cos and powers of x1 and x2.
        PySR is configured with operators that can construct such functions.
        """
        model = PySRRegressor(
            niterations=45,
            populations=16,
            population_size=40,
            maxsize=28,
            binary_operators=["+", "-", "*", "/", "pow"],
            unary_operators=["sin", "cos", "exp", "log"],
            procs=8,  # Utilize 8 vCPUs as specified in the environment
            random_state=42,
            verbosity=0,
            progress=False,
            model_selection="best",
        )

        model.fit(X, y, variable_names=["x1", "x2"])

        try:
            # Check if PySR found any equations
            if model.equations_.empty:
                raise IndexError("PySR did not find any equations.")

            # Get the best expression as a sympy object and convert to string
            best_sympy_expr = model.sympy()
            expression_str = str(best_sympy_expr)
            
            # Generate predictions from the best model
            predictions = model.predict(X)
            
            # Extract complexity from the results dataframe
            # The last row corresponds to the selected best equation
            best_equation_details = model.equations_.iloc[-1]
            complexity = int(best_equation_details['complexity'])

        except (IndexError, AttributeError, ValueError):
            # Fallback if PySR fails to find a suitable equation
            expression_str = "0.0"
            predictions = np.zeros_like(y)
            complexity = 0

        # Prepare the 'details' dictionary
        details = {}
        if complexity > 0:
            details["complexity"] = complexity
            
        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": details,
        }
