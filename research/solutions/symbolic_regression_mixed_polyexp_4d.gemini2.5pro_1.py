import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        Initializes the Solution class for the symbolic regression problem.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Learns a closed-form symbolic expression for the given 4D dataset using PySR.

        Args:
            X: Feature matrix of shape (n, 4).
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the learned expression, predictions, and details.
        """
        # PySR is configured for a higher-dimensional problem, requiring more search effort.
        # Parameters like niterations, populations, and population_size are increased.
        model = PySRRegressor(
            # --- Search Configuration ---
            niterations=120,          # More iterations for the 4D search space
            populations=40,           # Use more populations for better parallelism and diversity
            population_size=50,       # Larger populations to hold more diverse equations
            
            # --- Operators ---
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "cos", "sin", "log"],

            # --- Complexity Control ---
            maxsize=35,               # Allow for reasonably complex expressions needed for 4D
            parsimony=0.001,          # A small complexity penalty to favor simpler models
            
            # --- Stability and Constraints ---
            nested_constraints={      # Prevent trivial nesting like exp(exp(x))
                "exp": 1, 
                "log": 1,
                "sin": 1,
                "cos": 1,
            },
            patience=10,              # Enable early stopping if the score doesn't improve
            
            # --- Environment and Performance ---
            procs=0,                  # Use all available CPU cores
            
            # --- Loss and Reproducibility ---
            loss="L2DistLoss()",      # Standard L2 loss (Mean Squared Error)
            random_state=42,
            
            # --- Suppress Console Output ---
            verbosity=0,
            progress=False,
        )

        try:
            # Fit the model to the data
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

            # Check if any valid equations were discovered
            if not hasattr(model, 'equations_') or model.equations_.empty:
                raise ValueError("PySR did not find any equations.")

            # Retrieve the best symbolic expression (selected by score)
            best_sympy_expr = model.sympy()
            expression = str(best_sympy_expr)

            # Generate predictions from the best model
            predictions = model.predict(X)

            # Extract the complexity of the best model from the results dataframe
            df = model.equations_
            best_eq_row = df.iloc[df['score'].idxmax()]
            complexity = int(best_eq_row['complexity'])
            
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"complexity": complexity}
            }

        except (ValueError, RuntimeError, IndexError, ZeroDivisionError):
            # Fallback to a linear model if PySR fails, finds no equations, or errors out.
            A = np.c_[X, np.ones(X.shape[0])]
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                
                parts = [f"{c:.8f}*x{i+1}" for i, c in enumerate(coeffs[:-1])]
                parts.append(f"{coeffs[-1]:.8f}")
                
                expression = " + ".join(parts).replace("+ -", "- ")
                
                predictions = A @ coeffs

                # Complexity for a*x1 + b*x2 + c*x3 + d*x4 + e:
                # 4 multiplications, 4 additions => 8 binary ops => C = 16
                details = {"complexity": 16}

            except np.linalg.LinAlgError:
                # Ultimate fallback if linear regression fails: predict the mean
                mean_y = np.mean(y)
                expression = f"{mean_y:.8f}"
                predictions = np.full_like(y, mean_y)
                details = {"complexity": 0}
            
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": details
            }