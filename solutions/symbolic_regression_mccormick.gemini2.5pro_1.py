import numpy as np
import sympy as sp
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        Initializes the Solution class.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Learns a symbolic expression that fits the data.

        Args:
            X: Feature matrix of shape (n, 2).
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the learned expression and other details.
        """
        # The McCormick function is known to have trigonometric and polynomial terms.
        # Configure PySR to search for expressions with these components.
        # Parameters are tuned for a balance of performance and accuracy on an 8-core CPU.
        model = PySRRegressor(
            niterations=60,
            populations=32,
            population_size=40,
            procs=8,
            maxsize=25,
            
            # Operators present in the McCormick function family
            binary_operators=["+", "-", "*", "**"],
            unary_operators=["sin", "cos"],
            
            # For deterministic results and clean output
            random_state=42,
            verbosity=0,
            progress=False,

            # Help PySR find optimal constants
            optimizer_nrestarts=3,
            
            # Default selection strategy is 'best', which balances accuracy and complexity.
            model_selection="best",
        )

        # Fit the model to the provided data
        model.fit(X, y, variable_names=["x1", "x2"])

        # Handle the case where PySR fails to find any equations
        if not hasattr(model, 'equations_') or model.equations_.empty:
            # Fallback to a simple linear model as a last resort
            A = np.c_[X, np.ones(X.shape[0])]
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                expression = f"{coeffs[0]}*x1 + {coeffs[1]}*x2 + {coeffs[2]}"
                complexity = 4 # 2 multiplications, 2 additions
            except np.linalg.LinAlgError:
                expression = "0.0"
                complexity = 0
            
            return {
                "expression": expression,
                "predictions": None,
                "details": {
                    "complexity": complexity,
                    "status": "PySR failed, using fallback."
                }
            }

        # Get the best symbolic expression found by PySR
        best_expr_sympy = model.sympy()

        # Use sympy to simplify the expression, which can reduce its complexity
        simplified_expr = sp.simplify(best_expr_sympy)

        # Convert the simplified expression to a Python-evaluable string
        expression_str = str(simplified_expr)

        # Extract the complexity of the best model from the PySR results
        complexity = int(model.equations_.iloc[-1]['complexity'])

        return {
            "expression": expression_str,
            # Omitting predictions allows the evaluator to compute them from the expression,
            # ensuring consistency.
            "predictions": None,
            "details": {
                "complexity": complexity,
            }
        }
