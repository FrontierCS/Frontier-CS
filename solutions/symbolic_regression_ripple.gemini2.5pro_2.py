import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the ripple dataset using PySR with feature engineering.
        """
        x1_data = X[:, 0]
        x2_data = X[:, 1]
        
        # Feature Engineering: Add a radial basis feature r^2 = x1^2 + x2^2.
        # This is motivated by the "concentric wave patterns" description, which suggests
        # a dependency on the distance from the origin. This simplifies the search for PySR.
        r2_data = x1_data**2 + x2_data**2
        
        X_extended = np.column_stack([X, r2_data])
        
        # Configure PySRRegressor for the 8-core CPU environment.
        # Hyperparameters are tuned for a balance of search depth and runtime.
        model = PySRRegressor(
            niterations=120,
            populations=16,
            population_size=50,
            procs=8,
            maxsize=30,
            binary_operators=["+", "-", "*"],
            unary_operators=["sin", "cos"],
            nested_constraints={
                "sin": {"sin": 0, "cos": 0},
                "cos": {"sin": 0, "cos": 0}
            },
            random_state=42,
            verbosity=0,
            progress=False,
            temp_equation_file=True,
            model_selection="best"
        )
        
        # Fit the model on the data with the extended feature set.
        model.fit(X_extended, y, variable_names=["x1", "x2", "r2"])
        
        if not hasattr(model, 'equations_') or len(model.equations_) == 0:
            # Fallback if PySR finds no valid equations.
            expression = "0.0"
            predictions = np.zeros_like(y)
        else:
            # Retrieve the best symbolic expression.
            # It will be in terms of x1, x2, and the engineered feature r2.
            best_expr_sympy_with_r2 = model.sympy()
            
            # Define symbolic variables for substitution.
            r2_sym = sympy.Symbol('r2')
            x1_sym = sympy.Symbol('x1')
            x2_sym = sympy.Symbol('x2')
            
            # Substitute the 'r2' placeholder with its definition (x1**2 + x2**2).
            r2_definition = x1_sym**2 + x2_sym**2
            final_expr_sympy = best_expr_sympy_with_r2.subs(r2_sym, r2_definition)
            
            # Convert the final sympy object to the required string format.
            expression = str(final_expr_sympy)
            
            # Generate predictions using the fitted model.
            predictions = model.predict(X_extended)
            
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
