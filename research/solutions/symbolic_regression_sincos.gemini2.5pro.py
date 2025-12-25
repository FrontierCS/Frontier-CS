import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        """
        Initialize the Solution class.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Learn a closed-form symbolic expression for the given data.

        Args:
            X: Feature matrix of shape (n, 2) with columns 'x1', 'x2'.
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the symbolic expression, predictions, and details.
        """
        # Configure the PySR regressor.
        # The parameters are chosen to balance search time and solution quality,
        # tailored to the likely structure of the "SinCos" dataset.
        model = PySRRegressor(
            niterations=40,
            populations=24,
            population_size=50,
            binary_operators=["+", "-", "*", "/"],
            # The dataset name is a strong hint to focus on trigonometric functions.
            unary_operators=["sin", "cos"],
            maxsize=20,  # Limit complexity to prevent overfitting.
            model_selection="best", # Selects the equation with the best score (accuracy vs complexity).
            loss="L2DistLoss()",  # Corresponds to Mean Squared Error.
            procs=0,  # Use all available CPU cores.
            random_state=42,
            verbosity=0,
            progress=False,
            temp_equation_file=True, # For robustness on long runs.
            # Stop early if a very accurate expression is found.
            early_stop_condition=1e-7,
        )

        try:
            # Fit the model to the data.
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # PySR can sometimes raise errors (e.g., from the Julia backend).
            # We handle this by setting the model to None and using a fallback.
            model = None

        if model is None or not hasattr(model, 'equations_') or model.equations_.empty:
            # If PySR fails or finds no valid equations, return a simple fallback.
            expression = "0.0"
            predictions = np.zeros_like(y)
            complexity = 0
        else:
            # Get the best expression found by PySR.
            # model.sympy() returns the best equation as a sympy object.
            best_sympy_expr = model.sympy()
            expression = str(best_sympy_expr)
            
            # Generate predictions using the best model.
            # model.predict() defaults to the best equation.
            predictions = model.predict(X)

            # Calculate complexity based on the problem's scoring formula:
            # C = 2 * (#binary ops) + (#unary ops)
            try:
                # Parse the expression string back into a sympy object to traverse its structure.
                s_expr = sympy.sympify(expression)
                
                num_binary_ops = 0
                num_unary_ops = 0
                
                # Define the types of nodes to count as unary or binary operators.
                allowed_unary = (sympy.sin, sympy.cos, sympy.exp, sympy.log)
                # sympy represents -, / using Add, Mul, and Pow.
                allowed_binary = (sympy.Add, sympy.Mul, sympy.Pow)

                # Traverse the expression tree to count operators.
                for sub_expr in sympy.preorder_traversal(s_expr):
                    if isinstance(sub_expr, allowed_binary):
                        # An n-ary operator node corresponds to (n-1) binary operations.
                        num_binary_ops += len(sub_expr.args) - 1
                    elif isinstance(sub_expr, allowed_unary):
                        num_unary_ops += 1
                
                complexity = 2 * num_binary_ops + num_unary_ops
            except Exception:
                # Fallback if complexity calculation fails for any reason.
                complexity = 1000

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity},
        }
