import numpy as np


class Solution:
    def __init__(self, **kwargs):
        # Hyperparameters with reasonable defaults
        self.importance_threshold = kwargs.get("importance_threshold", 0.02)
        self.max_features = kwargs.get("max_features", 6)
        self.zero_tol = kwargs.get("zero_tol", 1e-8)

    def _format_number(self, x: float) -> str:
        return f"{float(x):.12g}"

    def _build_expression(self, items):
        # items: list of (coeff, expr_str or None for constant)
        if not items:
            return "0"

        parts = []
        first = True
        for coeff, expr in items:
            val = float(coeff)

            if expr is None:
                # Constant term
                if first:
                    parts.append(self._format_number(val))
                else:
                    if val >= 0:
                        parts.append(" + " + self._format_number(val))
                    else:
                        parts.append(" - " + self._format_number(-val))
            else:
                abs_val = abs(val)
                if first:
                    sign_str = "-" if val < 0 else ""
                else:
                    sign_str = " - " if val < 0 else " + "

                if np.isclose(abs_val, 1.0, rtol=1e-8, atol=1e-8):
                    coeff_str = ""
                else:
                    coeff_str = self._format_number(abs_val) + "*"

                term = f"{sign_str}{coeff_str}{expr}"
                parts.append(term)

            first = False

        return "".join(parts)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        n_samples = X.shape[0]
        if n_samples == 0 or y.size == 0:
            expression = "0"
            return {
                "expression": expression,
                "predictions": [],
                "details": {}
            }

        x1 = X[:, 0]
        x2 = X[:, 1]

        feature_exprs = []
        feature_values_list = []

        def add_feature(expr_str, values):
            feature_exprs.append(expr_str)
            feature_values_list.append(values)

        # Polynomial features
        add_feature("x1", x1)
        add_feature("x2", x2)
        add_feature("x1**2", x1 ** 2)
        add_feature("x2**2", x2 ** 2)
        add_feature("x1*x2", x1 * x2)

        # Trigonometric features with different frequencies
        freqs = [0.5, 1.0, 2.0]
        for var_name, arr in (("x1", x1), ("x2", x2)):
            for freq in freqs:
                if freq == 1.0:
                    arg_expr = var_name
                    arg_values = arr
                else:
                    arg_expr = f"{self._format_number(freq)}*{var_name}"
                    arg_values = freq * arr

                add_feature(f"sin({arg_expr})", np.sin(arg_values))
                add_feature(f"cos({arg_expr})", np.cos(arg_values))

        # Cross trigonometric interactions
        sin_x1 = np.sin(x1)
        cos_x1 = np.cos(x1)
        sin_x2 = np.sin(x2)
        cos_x2 = np.cos(x2)

        add_feature("sin(x1)*sin(x2)", sin_x1 * sin_x2)
        add_feature("cos(x1)*cos(x2)", cos_x1 * cos_x2)
        add_feature("sin(x1)*cos(x2)", sin_x1 * cos_x2)
        add_feature("cos(x1)*sin(x2)", cos_x1 * sin_x2)

        # Sum/difference inside trig
        add_feature("sin(x1 + x2)", np.sin(x1 + x2))
        add_feature("cos(x1 + x2)", np.cos(x1 + x2))
        add_feature("sin(x1 - x2)", np.sin(x1 - x2))
        add_feature("cos(x1 - x2)", np.cos(x1 - x2))

        if feature_values_list:
            F = np.column_stack(feature_values_list)
        else:
            F = np.empty((n_samples, 0), dtype=float)

        n_features = F.shape[1]
        ones = np.ones(n_samples, dtype=float)

        # Initial regression with all features
        if n_features > 0:
            A_full = np.column_stack([F, ones])
        else:
            A_full = ones.reshape(-1, 1)

        coefs_full, _, _, _ = np.linalg.lstsq(A_full, y, rcond=None)
        intercept_full = coefs_full[-1]
        if n_features > 0:
            coefs_features_full = coefs_full[:-1]
        else:
            coefs_features_full = np.array([], dtype=float)

        # Feature importance-based selection
        selected_indices = []
        if n_features > 0:
            stds = np.std(F, axis=0)
            scales = np.where(stds > 0, stds, 1.0)
            importances = np.abs(coefs_features_full) * scales
            max_imp = float(np.max(importances)) if importances.size > 0 else 0.0

            if max_imp > 0 and not np.isnan(max_imp):
                threshold_level = max_imp * self.importance_threshold
                sorted_idx = np.argsort(importances)[::-1]
                for j in sorted_idx:
                    if importances[j] < threshold_level:
                        break
                    selected_indices.append(int(j))
                    if len(selected_indices) >= self.max_features:
                        break

        # Refit with selected features
        if selected_indices:
            F_sel = F[:, selected_indices]
            A_sel = np.column_stack([F_sel, ones])
            coefs_sel, _, _, _ = np.linalg.lstsq(A_sel, y, rcond=None)
            coefs_features_sel = coefs_sel[:-1]
            intercept_sel = coefs_sel[-1]
            y_pred = A_sel @ coefs_sel
        else:
            # Only intercept: mean of y
            intercept_sel = float(np.mean(y))
            coefs_features_sel = np.array([], dtype=float)
            y_pred = np.full_like(y, intercept_sel, dtype=float)

        # Build expression
        items = []
        if abs(intercept_sel) > self.zero_tol or not selected_indices:
            items.append((intercept_sel, None))

        for coef, idx in zip(coefs_features_sel, selected_indices):
            if abs(coef) <= self.zero_tol:
                continue
            expr_str = feature_exprs[idx]
            items.append((coef, expr_str))

        expression = self._build_expression(items)

        return {
            "expression": expression,
            "predictions": y_pred.tolist(),
            "details": {}
        }