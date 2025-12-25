import numpy as np
from itertools import product


class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        expression = None

        # Try PySR-based symbolic regression
        try:
            from pysr import PySRRegressor

            model = PySRRegressor(
                niterations=50,
                binary_operators=["+", "-", "*", "^"],
                unary_operators=["exp"],
                populations=20,
                population_size=40,
                maxsize=25,
                verbosity=0,
                progress=False,
                random_state=42,
            )
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
            best_expr = model.sympy()
            if best_expr is not None:
                expression = str(best_expr)
        except Exception:
            expression = None

        # Fallback to polynomial regression if PySR is unavailable or fails
        if not isinstance(expression, str) or not expression:
            expression = self._fallback_polynomial(X, y)

        return {
            "expression": expression,
            "predictions": None,
            "details": {},
        }

    def _fallback_polynomial(self, X: np.ndarray, y: np.ndarray, degree: int = 4) -> str:
        n_samples, n_features = X.shape
        n_vars = min(4, n_features)
        X_use = X[:, :n_vars]

        # Build polynomial feature matrix up to the specified degree
        features = [np.ones(n_samples, dtype=float)]
        exponents_list = []

        for exps in product(range(degree + 1), repeat=n_vars):
            total_deg = sum(exps)
            if total_deg == 0 or total_deg > degree:
                continue
            exponents_list.append(exps)
            term = np.ones(n_samples, dtype=float)
            for j, power in enumerate(exps):
                if power:
                    term *= X_use[:, j] ** power
            features.append(term)

        A = np.column_stack(features)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        expression = self._build_polynomial_expression(coeffs, exponents_list)
        return expression

    def _build_polynomial_expression(
        self,
        coeffs: np.ndarray,
        exponents_list,
        coeff_tol: float = 1e-12,
    ) -> str:
        # Constant term
        const = float(coeffs[0])
        expression = f"{const:.12g}"

        # Non-constant terms
        for coef, exps in zip(coeffs[1:], exponents_list):
            coef = float(coef)
            if abs(coef) < coeff_tol:
                continue

            mon_parts = []
            for var_idx, power in enumerate(exps):
                if power == 0:
                    continue
                var_name = f"x{var_idx + 1}"
                if power == 1:
                    mon_parts.append(var_name)
                else:
                    mon_parts.append(f"{var_name}**{power}")
            mon_expr = "*".join(mon_parts) if mon_parts else "1"

            sign = "+" if coef >= 0 else "-"
            coef_abs = abs(coef)
            expression += f" {sign} {coef_abs:.12g}*{mon_expr}"

        if not expression:
            expression = "0"
        return expression
