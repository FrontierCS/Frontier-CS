import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        Initialize the solution by configuring the PySR regressor.
        The parameters are tuned for the CPU-only environment with 8 vCPUs.
        """
        self.model = PySRRegressor(
            niterations=100,          # Increased iterations for a more thorough search
            populations=32,           # More populations for diversity (multiple of procs)
            population_size=50,       # Larger size for each population
            
            # Define the set of allowed operators based on problem specification
            binary_operators=["+", "-", "*", "/", "pow"],  # 'pow' is for '**'
            unary_operators=["sin", "cos", "exp", "log"],
            
            # Constraints to simplify the search space by avoiding unlikely nested functions
            nested_constraints={
                'sin': {'sin': 0, 'cos': 0},
                'cos': {'sin': 0, 'cos': 0},
            },
            
            maxsize=30,               # Allow for reasonably complex expressions
            
            # Parallelization settings to match the environment
            procs=8,
            
            # For reproducibility
            random_state=42,

            # Speed up evaluation on large datasets. PySR will select a batch size.
            batching=True,
            
            # Use annealing to help the search converge
            annealing=True,

            # Use float64 for higher precision
            precision=64,

            # Suppress verbose output during execution
            verbosity=0,
            progress=False,

            # Let PySR select the best model based on its score (accuracy vs complexity)
            model_selection="best",
        )

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data using PySR.

        Args:
            X: Feature matrix of shape (n, 2) with columns x1, x2
            y: Target values of shape (n,)

        Returns:
            A dictionary containing the symbolic expression, predictions, and details.
        """
        
        # Fit the PySR model to the provided data
        try:
            self.model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # In case of any unexpected errors during fitting, fall back.
            return self._fallback(X, y)

        # Check if any equations were found
        if not hasattr(self.model, 'equations_') or self.model.equations_.empty:
            # Fallback to a simple model if PySR fails to find any expression
            return self._fallback(X, y)

        # Get the best expression using sympy for a clean, Python-compatible format
        sympy_expr = self.model.sympy()
        expression_str = str(sympy_expr)

        # Generate predictions using the best-found model
        predictions = self.model.predict(X)

        # Extract PySR's own complexity score for the details dictionary
        pysr_complexity = self.model.equations_.iloc[-1]['complexity']

        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": {"complexity": int(pysr_complexity)}
        }

    def _fallback(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        A fallback method in case PySR fails, providing a simple linear regression model.
        """
        x1, x2 = X[:, 0], X[:, 1]
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
        except np.linalg.LinAlgError:
            # If lstsq fails (e.g., singular matrix), predict the mean
            a, b, c = 0.0, 0.0, np.mean(y)

        expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
        predictions = a * x1 + b * x2 + c

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"fallback": True}
        }