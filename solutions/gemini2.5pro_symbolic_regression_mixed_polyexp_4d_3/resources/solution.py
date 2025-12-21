import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Learns a symbolic expression for the given data using PySR.

        Args:
            X: Feature matrix of shape (n, 4)
            y: Target values of shape (n,)

        Returns:
            A dictionary containing the learned expression and other details.
        """
        # Handle the trivial case of a constant target variable to avoid PySR errors.
        if np.std(y) < 1e-9:
            mean_y = np.mean(y)
            return {
                "expression": f"{mean_y:.8f}",
                "predictions": np.full_like(y, mean_y),
                "details": {"complexity": 0}
            }

        # Configure PySRRegressor with parameters tuned for a 4D problem
        # on an 8-core CPU environment. The search parameters are increased
        # to handle the higher dimensionality.
        model = PySRRegressor(
            niterations=120,
            populations=32,
            population_size=50,
            maxsize=35,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "cos", "sin"],
            nested_constraints={
                "exp": {"exp": 0, "cos": 0, "sin": 0},
                "cos": {"exp": 0, "cos": 0, "sin": 0},
                "sin": {"exp": 0, "cos": 0, "sin": 0},
            },
            procs=8,
            deterministic=True,
            random_state=42,
            temp_equation_file=True,
            verbosity=0,
            progress=False,
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        except Exception:
            # Catch potential errors during fitting, e.g., memory issues
            pass

        # If PySR fails or finds no equations, fall back to a linear model.
        if not hasattr(model, 'equations_') or len(model.equations_) == 0:
            try:
                A = np.c_[X, np.ones(X.shape[0])]
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                expression = (f"{coeffs[0]:.6f}*x1 + {coeffs[1]:.6f}*x2 + "
                              f"{coeffs[2]:.6f}*x3 + {coeffs[3]:.6f}*x4 + {coeffs[4]:.6f}")
            except np.linalg.LinAlgError:
                expression = str(np.mean(y)) # Final fallback
            
            return {
                "expression": expression,
                "predictions": None,
                "details": {}
            }

        # Retrieve the best expression found by PySR.
        best_expression_sympy = model.sympy()
        expression_str = str(best_expression_sympy)

        # Generate predictions from the best model.
        predictions = model.predict(X)

        # Provide PySR's internal complexity measure (node count).
        best_idx = model.equations_.score.idxmax()
        pysr_complexity = int(model.equations_.loc[best_idx, 'complexity'])

        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": {
                "complexity": pysr_complexity
            }
        }
