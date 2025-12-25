import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        if X.shape[1] != 2:
            raise ValueError("Expected X with shape (n, 2)")

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Precompute basic trigonometric features
        ones = np.ones_like(x1)

        sin_x1 = np.sin(x1)
        cos_x1 = np.cos(x1)
        sin_x2 = np.sin(x2)
        cos_x2 = np.cos(x2)

        sin_2x1 = np.sin(2.0 * x1)
        cos_2x1 = np.cos(2.0 * x1)
        sin_2x2 = np.sin(2.0 * x2)
        cos_2x2 = np.cos(2.0 * x2)

        sinx1_sinx2 = sin_x1 * sin_x2
        sinx1_cosx2 = sin_x1 * cos_x2
        cosx1_sinx2 = cos_x1 * sin_x2
        cosx1_cosx2 = cos_x1 * cos_x2

        features = [
            ones,
            sin_x1,
            cos_x1,
            sin_x2,
            cos_x2,
            sin_2x1,
            cos_2x1,
            sin_2x2,
            cos_2x2,
            sinx1_sinx2,
            sinx1_cosx2,
            cosx1_sinx2,
            cosx1_cosx2,
        ]

        names = [
            "1",
            "sin(x1)",
            "cos(x1)",
            "sin(x2)",
            "cos(x2)",
            "sin(2*x1)",
            "cos(2*x1)",
            "sin(2*x2)",
            "cos(2*x2)",
            "sin(x1)*sin(x2)",
            "sin(x1)*cos(x2)",
            "cos(x1)*sin(x2)",
            "cos(x1)*cos(x2)",
        ]

        # Internal operation counts for each basis (excluding coefficient and outer pluses)
        # (binary_ops_inside, unary_ops_inside)
        binary_internal = [
            0,  # 1
            0,  # sin(x1)
            0,  # cos(x1)
            0,  # sin(x2)
            0,  # cos(x2)
            1,  # sin(2*x1): 2*x1
            1,  # cos(2*x1): 2*x1
            1,  # sin(2*x2): 2*x2
            1,  # cos(2*x2): 2*x2
            1,  # sin(x1)*sin(x2)
            1,  # sin(x1)*cos(x2)
            1,  # cos(x1)*sin(x2)
            1,  # cos(x1)*cos(x2)
        ]

        unary_internal = [
            0,  # 1
            1,  # sin(x1)
            1,  # cos(x1)
            1,  # sin(x2)
            1,  # cos(x2)
            1,  # sin(2*x1)
            1,  # cos(2*x1)
            1,  # sin(2*x2)
            1,  # cos(2*x2)
            2,  # sin(x1)*sin(x2)
            2,  # sin(x1)*cos(x2)
            2,  # cos(x1)*sin(x2)
            2,  # cos(x1)*cos(x2)
        ]

        Phi = np.column_stack(features)

        # Linear least squares fit
        w, *_ = np.linalg.lstsq(Phi, y, rcond=None)

        if w.size == 0:
            expression = "0"
            predictions = np.zeros_like(y)
            details = {"complexity": 0}
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": details,
            }

        max_abs_coef = float(np.max(np.abs(w)))
        if max_abs_coef == 0.0:
            expression = "0"
            predictions = np.zeros_like(y)
            details = {"complexity": 0}
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": details,
            }

        # Threshold small coefficients
        tol = max(1e-6, max_abs_coef * 1e-3)
        selected = [i for i, c in enumerate(w) if abs(c) >= tol]

        if not selected:
            selected = [int(np.argmax(np.abs(w)))]

        # Simplified coefficient vector
        w_simplified = np.zeros_like(w)
        for i in selected:
            w_simplified[i] = w[i]

        # Snap coefficients close to integers to the nearest integer
        for i in selected:
            c = w_simplified[i]
            nearest_int = np.round(c)
            if abs(c - nearest_int) <= max(1e-3, 1e-3 * max_abs_coef):
                w_simplified[i] = nearest_int

        # Build expression string and compute complexity
        n_terms_total = len(selected)
        expression_parts = []
        binary_ops = 0
        unary_ops = 0

        for order, idx in enumerate(selected):
            name = names[idx]
            c = float(w_simplified[idx])
            abs_c = abs(c)

            # Internal operations from the basis itself
            binary_ops += binary_internal[idx]
            unary_ops += unary_internal[idx]

            if name == "1":
                # Pure constant term
                if order == 0:
                    term_str = f"{c:.10g}"
                else:
                    if c >= 0:
                        term_str = f" + {abs_c:.10g}"
                    else:
                        term_str = f" - {abs_c:.10g}"
            else:
                # Non-constant basis
                is_one = np.isclose(abs_c, 1.0, rtol=1e-8, atol=1e-8)
                if is_one:
                    # No explicit multiplication by 1
                    if order == 0:
                        term_str = name if c >= 0 else f"-{name}"
                    else:
                        if c >= 0:
                            term_str = f" + {name}"
                        else:
                            term_str = f" - {name}"
                else:
                    # Explicit coefficient multiplication
                    binary_ops += 1  # coefficient * basis
                    coef_abs_str = f"{abs_c:.10g}"
                    if order == 0:
                        if c >= 0:
                            term_str = f"{coef_abs_str}*{name}"
                        else:
                            term_str = f"-{coef_abs_str}*{name}"
                    else:
                        if c >= 0:
                            term_str = f" + {coef_abs_str}*{name}"
                        else:
                            term_str = f" - {coef_abs_str}*{name}"

            expression_parts.append(term_str)

        expression = "".join(expression_parts) if expression_parts else "0"

        # Add binary operations for additions/subtractions between terms
        if n_terms_total >= 2:
            binary_ops += (n_terms_total - 1)

        complexity = 2 * binary_ops + unary_ops

        # Compute predictions using the simplified coefficients
        y_pred = Phi.dot(w_simplified)

        return {
            "expression": expression,
            "predictions": y_pred.tolist(),
            "details": {"complexity": int(complexity)},
        }
