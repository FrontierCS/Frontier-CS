import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        Initializes the Solution object. Any keyword arguments are ignored.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression that fits the given 4D data.

        This method uses the PySR library, a powerful tool for symbolic regression.
        The parameters for PySRRegressor are tuned to balance search breadth
        and depth, leveraging the available multi-core CPU environment. The
        operator set is specifically chosen based on the problem's name,
        "Mixed PolyExp 4D", to focus the search on polynomial and exponential
        combinations.

        Args:
            X: Feature matrix of shape (n, 4) with columns x1, x2, x3, x4.
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the symbolic expression, predictions,
            and model complexity details.
        """
        model = PySRRegressor(
            # Run for a sufficient number of iterations for a 4D problem.
            niterations=60,
            
            # Use a large number of parallel populations to leverage the 8 vCPUs.
            populations=40,
            population_size=50,
            
            # Operators tailored to "PolyExp". A custom `square` operator is
            # more stable and efficient for finding polynomial terms than `pow`.
            binary_operators=["+", "*", "-"],
            unary_operators=["exp", "square(x) = x*x"],
            
            # Allow for reasonably complex expressions.
            maxsize=35,
            
            # Slightly increase parsimony to favor simpler, higher-scoring solutions.
            parsimony=0.005,
            
            # Explicitly use all 8 available CPU cores.
            procs=8,
            
            # Ensure deterministic results for reproducibility.
            random_state=42,
            
            # Suppress verbose output.
            verbosity=0,
            progress=False,
            
            # Employ advanced search strategies to escape local optima.
            annealing=True,
            use_frequency=True,
            
            # Prevent pathological nested expressions like exp(exp(x)).
            nested_constraints={"exp": {"exp": 0}, "square": {"square": 0}},
            
            # Set a timeout as a safeguard against unexpectedly long runs.
            timeout_in_seconds=360
        )

        try:
            # Fit the model, specifying variable names for the output expression.
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        except Exception:
            # Catch potential errors during PySR fit, such as timeouts.
            pass
        
        # Check if the search was successful and at least one equation was found.
        if not hasattr(model, 'equations_') or model.equations_.empty:
            # If PySR fails or finds no equations, fallback to a simple constant model.
            mean_y = np.mean(y)
            expression = str(mean_y)
            predictions = np.full_like(y, mean_y)
            complexity = 0
        else:
            # Retrieve the best-scoring equation found by PySR.
            best_equation = model.get_best()
            
            # Convert the sympy representation of the equation to a string.
            expression_sympy = best_equation.sympy_format
            expression = str(expression_sympy)
            
            # Generate predictions using the best model.
            predictions = model.predict(X)
            
            # Extract the complexity of the best equation.
            complexity = best_equation.complexity

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": int(complexity)}
        }
