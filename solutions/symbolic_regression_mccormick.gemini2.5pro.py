import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        No-op constructor.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the McCormick dataset using PySR.

        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            A dictionary containing the symbolic expression and optional details.
        """
        # The McCormick function is f(x1, x2) = sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1
        # This suggests that sin, +, -, and ** are important operators.
        
        model = PySRRegressor(
            # Search configuration
            niterations=60,         # More iterations for a better search
            populations=32,         # Number of populations to evolve
            population_size=50,     # Number of expressions in each population

            # Operators based on the known form of the McCormick function
            binary_operators=["+", "-", "*", "**"],
            unary_operators=["sin", "cos"],

            # Complexity control
            maxsize=30,             # Maximum complexity of any expression
            parsimony=0.001,        # A small penalty for complexity to favor simpler models

            # Environment and parallelism
            procs=8,                # Use all 8 available vCPUs

            # Reproducibility and logging
            random_state=42,
            verbosity=0,
            progress=False,

            # Early stopping for efficiency
            # Stop if a very accurate and simple model is found.
            # The metric is f(loss, complexity) = loss + parsimony * complexity.
            early_stop_condition="f(loss, complexity) < 1e-8",

            # Other settings
            # Ensure both features are used in the search
            select_k_features=2,
            # Use a robust loss function against outliers
            loss="L1DistLoss()",
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # Catch potential errors during PySR execution
            pass

        # Fallback to a simpler model if PySR fails or finds no equations
        if not hasattr(model, 'equations_') or model.equations_.shape[0] == 0:
            try:
                A = np.c_[X, np.ones(X.shape[0])]
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                expression = f"{coeffs[0]}*x1 + {coeffs[1]}*x2 + {coeffs[2]}"
            except np.linalg.LinAlgError:
                expression = "0.0"  # Ultimate fallback
            
            return {"expression": expression}

        # Get the best equation based on the score (loss and complexity)
        best_equation = model.get_best()
        
        # Convert the sympy expression to a Python-evaluable string
        expression = str(best_equation.sympy_format)
        
        # Extract complexity for the details dictionary
        complexity = best_equation.complexity

        return {
            "expression": expression,
            "predictions": None,  # Evaluator will compute predictions from the expression
            "details": {
                "complexity": int(complexity)
            }
        }
