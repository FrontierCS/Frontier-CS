import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def _solve_with_pysr(self, X: np.ndarray, y: np.ndarray):
        from pysr import PySRRegressor

        model = PySRRegressor(
            niterations=80,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=15,
            population_size=33,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
        )
        model.fit(X, y, variable_names=["x1", "x2"])

        best_expr = model.sympy()
        expression = str(best_expr)
        predictions = model.predict(X)
        return expression, predictions

    def _solve_with_linear_basis(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]

        r2 = x1**2 + x2**2
        r = np.sqrt(r2)

        basis = [
            ("1", np.ones_like(x1)),
            ("x1", x1),
            ("x2", x2),
            ("x1**2 + x2**2", r2),
            ("x1**2 - x2**2", x1**2 - x2**2),
            ("x1*x2", x1 * x2),
            ("sin(x1)", np.sin(x1)),
            ("cos(x1)", np.cos(x1)),
            ("sin(x2)", np.sin(x2)),
            ("cos(x2)", np.cos(x2)),
            ("sin(x1 + x2)", np.sin(x1 + x2)),
            ("cos(x1 + x2)", np.cos(x1 + x2)),
            ("sin(x1**2 + x2**2)", np.sin(r2)),
            ("cos(x1**2 + x2**2)", np.cos(r2)),
            ("(x1**2 + x2**2)*sin(x1**2 + x2**2)", r2 * np.sin(r2)),
            ("(x1**2 + x2**2)*cos(x1**2 + x2**2)", r2 * np.cos(r2)),
            ("sin(3*(x1**2 + x2**2))", np.sin(3 * r2)),
            ("cos(3*(x1**2 + x2**2))", np.cos(3 * r2)),
            ("sin((x1**2 + x2**2)**0.5)", np.sin(r)),
            ("cos((x1**2 + x2**2)**0.5)", np.cos(r)),
            ("sin(x1**2 - x2**2)", np.sin(x1**2 - x2**2)),
            ("cos(x1**2 - x2**2)", np.cos(x1**2 - x2**2)),
        ]

        A = np.column_stack([b[1] for b in basis])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        threshold = 1e-8
        terms = []
        kept_indices = []
        for idx, (coef, (expr_str, _)) in enumerate(zip(coeffs, basis)):
            if abs(coef) < threshold:
                continue
            kept_indices.append(idx)
            if expr_str == "1":
                term = f"({coef:.12g})"
            else:
                term = f"({coef:.12g})*({expr_str})"
            terms.append(term)

        if not terms:
            expression = "0"
            predictions = np.zeros_like(y)
        else:
            expression = " + ".join(terms)
            A_kept = A[:, kept_indices]
            coeffs_kept = coeffs[kept_indices]
            predictions = A_kept.dot(coeffs_kept)

        return expression, predictions

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        try:
            expression, predictions = self._solve_with_pysr(X, y)
        except Exception:
            expression, predictions = self._solve_with_linear_basis(X, y)

        if isinstance(predictions, np.ndarray):
            predictions = predictions.tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }