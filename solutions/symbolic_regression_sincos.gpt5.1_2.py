import numpy as np

try:
    from pysr import PySRRegressor
    _HAS_PYSR = True
except Exception:
    PySRRegressor = None
    _HAS_PYSR = False


class Solution:
    def __init__(self, **kwargs):
        self.use_pysr = bool(kwargs.get("use_pysr", True)) and _HAS_PYSR

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        expression = None
        predictions = None

        if self.use_pysr:
            try:
                expression, predictions = self._solve_with_pysr(X, y)
            except Exception:
                expression, predictions = None, None

        if expression is None:
            expression, predictions = self._solve_with_trig_lstsq(X, y)

        if isinstance(predictions, np.ndarray):
            predictions = predictions.tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }

    def _solve_with_pysr(self, X: np.ndarray, y: np.ndarray):
        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos"],
            populations=10,
            population_size=33,
            maxsize=20,
            progress=False,
            verbosity=0,
            random_state=42,
            procs=0,
        )

        model.fit(X, y, variable_names=["x1", "x2"])

        best_expr = model.sympy()
        expression = str(best_expr)
        preds = np.asarray(model.predict(X), dtype=float).ravel()
        return expression, preds

    def _solve_with_trig_lstsq(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Basis functions: (expression_string, function)
        basis_info = [
            ("1", lambda a, b: np.ones_like(a)),
            ("x1", lambda a, b: a),
            ("x2", lambda a, b: b),
            ("sin(x1)", lambda a, b: np.sin(a)),
            ("cos(x1)", lambda a, b: np.cos(a)),
            ("sin(x2)", lambda a, b: np.sin(b)),
            ("cos(x2)", lambda a, b: np.cos(b)),
            ("sin(x1)*cos(x2)", lambda a, b: np.sin(a) * np.cos(b)),
            ("sin(x1)*sin(x2)", lambda a, b: np.sin(a) * np.sin(b)),
            ("cos(x1)*cos(x2)", lambda a, b: np.cos(a) * np.cos(b)),
            ("cos(x1)*sin(x2)", lambda a, b: np.cos(a) * np.sin(b)),
            ("sin(x1+x2)", lambda a, b: np.sin(a + b)),
            ("cos(x1+x2)", lambda a, b: np.cos(a + b)),
            ("sin(x1-x2)", lambda a, b: np.sin(a - b)),
            ("cos(x1-x2)", lambda a, b: np.cos(a - b)),
        ]

        n_samples = x1.shape[0]
        n_basis = len(basis_info)
        A = np.empty((n_samples, n_basis), dtype=float)
        for j, (_, func) in enumerate(basis_info):
            A[:, j] = func(x1, x2)

        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        order = np.argsort(-np.abs(coeffs))
        max_terms = min(6, n_basis)

        best_mse = np.inf
        best_idxs = None
        best_coeffs = None

        for k in range(1, max_terms + 1):
            idxs = order[:k]
            A_sub = A[:, idxs]
            c_sub, _, _, _ = np.linalg.lstsq(A_sub, y, rcond=None)
            y_pred = A_sub @ c_sub
            mse = np.mean((y - y_pred) ** 2)
            if mse < best_mse:
                best_mse = mse
                best_idxs = idxs
                best_coeffs = c_sub

        if best_idxs is None:
            # Fallback to simple mean model if something went wrong
            mean_y = float(np.mean(y))
            expression = f"{mean_y}"
            predictions = np.full_like(y, mean_y)
            return expression, predictions

        expression = self._build_expression(basis_info, best_idxs, best_coeffs)
        predictions = (A[:, best_idxs] @ best_coeffs)
        return expression, predictions

    def _build_expression(self, basis_info, idxs, coeffs):
        terms = []
        for j, coef in zip(idxs, coeffs):
            if abs(coef) < 1e-10:
                continue
            name = basis_info[j][0]
            if name == "1":
                term = f"({coef})"
            else:
                term = f"({coef})*{name}"
            terms.append(term)

        if not terms:
            return "0"
        return "+".join(terms)
