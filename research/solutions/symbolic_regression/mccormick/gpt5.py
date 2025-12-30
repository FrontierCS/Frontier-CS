import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.drop_tol = kwargs.get("drop_tol", 1e-10)
        self.coef_one_tol = kwargs.get("coef_one_tol", 1e-8)
        self.extra_threshold_ratio = kwargs.get("extra_threshold_ratio", 1e-6)

    def _format_number(self, x):
        return f"{x:.12g}"

    def _build_expression(self, coeffs, feature_names):
        core_map = {
            "sin_sum": "sin(x1 + x2)",
            "sq_diff": "(x1 - x2)**2",
            "x1": "x1",
            "x2": "x2",
            "const": None,
            "x1x2": "x1*x2",
            "x1_sq": "x1**2",
            "x2_sq": "x2**2",
            "cos_sum": "cos(x1 + x2)",
            "sin_x1": "sin(x1)",
            "sin_x2": "sin(x2)",
        }

        terms = []
        for name, c in zip(feature_names, coeffs):
            if abs(c) < self.drop_tol:
                continue

            if name == "const":
                term = self._format_number(abs(c))
                sign = "-" if c < 0 else "+"
                terms.append((sign, term))
                continue

            core = core_map[name]
            abs_c = abs(c)
            sign = "-" if c < 0 else "+"

            if abs(abs_c - 1.0) < self.coef_one_tol:
                term = core
            else:
                term = f"{self._format_number(abs_c)}*{core}"

            terms.append((sign, term))

        if not terms:
            return "0"

        first_sign, first_term = terms[0]
        expr = f"-{first_term}" if first_sign == "-" else first_term
        for sgn, trm in terms[1:]:
            if sgn == "+":
                expr += f" + {trm}"
            else:
                expr += f" - {trm}"
        return expr

    def _evaluate_expression(self, expression, x1, x2):
        env = {
            "__builtins__": {},
            "x1": x1,
            "x2": x2,
            "sin": np.sin,
            "cos": np.cos,
            "exp": np.exp,
            "log": np.log,
        }
        return eval(expression, env, {})

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0].astype(float)
        x2 = X[:, 1].astype(float)
        y = y.astype(float)

        # Base McCormick-like features
        base_features = [
            ("sin_sum", np.sin(x1 + x2)),
            ("sq_diff", (x1 - x2) ** 2),
            ("x1", x1),
            ("x2", x2),
            ("const", np.ones_like(y)),
        ]

        A_base = np.column_stack([f for _, f in base_features])
        coeffs_base, _, _, _ = np.linalg.lstsq(A_base, y, rcond=None)
        pred_base = A_base @ coeffs_base
        mse_base = np.mean((y - pred_base) ** 2)
        var_y = np.mean((y - y.mean()) ** 2) + 1e-12

        use_extra = mse_base / var_y > self.extra_threshold_ratio

        if use_extra:
            extra_features = [
                ("x1x2", x1 * x2),
                ("x1_sq", x1 ** 2),
                ("x2_sq", x2 ** 2),
                ("cos_sum", np.cos(x1 + x2)),
                ("sin_x1", np.sin(x1)),
                ("sin_x2", np.sin(x2)),
            ]
            all_features = base_features + extra_features
            A_all = np.column_stack([f for _, f in all_features])
            coeffs_all, _, _, _ = np.linalg.lstsq(A_all, y, rcond=None)
            feature_names = [n for n, _ in all_features]
            coeffs = coeffs_all
        else:
            feature_names = [n for n, _ in base_features]
            coeffs = coeffs_base

        expression = self._build_expression(coeffs, feature_names)
        predictions = self._evaluate_expression(expression, x1, x2)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }