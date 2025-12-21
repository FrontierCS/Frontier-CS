import numpy as np


class Solution:
    def __init__(self, max_terms: int = 8, **kwargs):
        self.max_terms = max_terms

    def _build_basis(self, x1: np.ndarray, x2: np.ndarray):
        sin_x1 = np.sin(x1)
        cos_x1 = np.cos(x1)
        sin_x2 = np.sin(x2)
        cos_x2 = np.cos(x2)

        x1_plus_x2 = x1 + x2
        x1_minus_x2 = x1 - x2
        x1_times_x2 = x1 * x2

        two_x1 = 2.0 * x1
        two_x2 = 2.0 * x2

        sin_x1_plus_x2 = np.sin(x1_plus_x2)
        cos_x1_plus_x2 = np.cos(x1_plus_x2)
        sin_x1_minus_x2 = np.sin(x1_minus_x2)
        cos_x1_minus_x2 = np.cos(x1_minus_x2)

        sin_x1_times_x2 = np.sin(x1_times_x2)
        cos_x1_times_x2 = np.cos(x1_times_x2)

        sin_2x1 = np.sin(two_x1)
        cos_2x1 = np.cos(two_x1)
        sin_2x2 = np.sin(two_x2)
        cos_2x2 = np.cos(two_x2)

        sin_x1_sq = sin_x1 * sin_x1
        cos_x1_sq = cos_x1 * cos_x1
        sin_x2_sq = sin_x2 * sin_x2
        cos_x2_sq = cos_x2 * cos_x2

        basis_values = []
        basis_exprs = []

        # Constant term
        basis_values.append(np.ones_like(x1))
        basis_exprs.append("1.0")

        # Basic sin/cos
        basis_values.append(sin_x1)
        basis_exprs.append("sin(x1)")

        basis_values.append(cos_x1)
        basis_exprs.append("cos(x1)")

        basis_values.append(sin_x2)
        basis_exprs.append("sin(x2)")

        basis_values.append(cos_x2)
        basis_exprs.append("cos(x2)")

        # Sum and difference
        basis_values.append(sin_x1_plus_x2)
        basis_exprs.append("sin(x1 + x2)")

        basis_values.append(cos_x1_plus_x2)
        basis_exprs.append("cos(x1 + x2)")

        basis_values.append(sin_x1_minus_x2)
        basis_exprs.append("sin(x1 - x2)")

        basis_values.append(cos_x1_minus_x2)
        basis_exprs.append("cos(x1 - x2)")

        # Product
        basis_values.append(sin_x1_times_x2)
        basis_exprs.append("sin(x1*x2)")

        basis_values.append(cos_x1_times_x2)
        basis_exprs.append("cos(x1*x2)")

        # Double angle
        basis_values.append(sin_2x1)
        basis_exprs.append("sin(2.0*x1)")

        basis_values.append(cos_2x1)
        basis_exprs.append("cos(2.0*x1)")

        basis_values.append(sin_2x2)
        basis_exprs.append("sin(2.0*x2)")

        basis_values.append(cos_2x2)
        basis_exprs.append("cos(2.0*x2)")

        # Products of sines and cosines
        basis_values.append(sin_x1 * sin_x2)
        basis_exprs.append("sin(x1)*sin(x2)")

        basis_values.append(sin_x1 * cos_x2)
        basis_exprs.append("sin(x1)*cos(x2)")

        basis_values.append(cos_x1 * sin_x2)
        basis_exprs.append("cos(x1)*sin(x2)")

        basis_values.append(cos_x1 * cos_x2)
        basis_exprs.append("cos(x1)*cos(x2)")

        # Squared terms
        basis_values.append(sin_x1_sq)
        basis_exprs.append("sin(x1)**2")

        basis_values.append(cos_x1_sq)
        basis_exprs.append("cos(x1)**2")

        basis_values.append(sin_x2_sq)
        basis_exprs.append("sin(x2)**2")

        basis_values.append(cos_x2_sq)
        basis_exprs.append("cos(x2)**2")

        B = np.column_stack(basis_values)
        return B, basis_exprs

    def _format_float(self, val: float) -> str:
        return f"{float(val):.12g}"

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        if y.size == 0:
            expression = "0.0"
            return {
                "expression": expression,
                "predictions": [],
                "details": {}
            }

        var_y = float(np.var(y))
        mean_y = float(np.mean(y))

        # If target is (almost) constant, return constant expression
        if not np.isfinite(var_y) or var_y <= 1e-12:
            expression = self._format_float(mean_y)
            predictions = np.full_like(y, mean_y, dtype=float)
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }

        n_samples, n_features = X.shape
        if n_features < 2:
            # Fallback to constant if input is malformed
            expression = self._format_float(mean_y)
            predictions = np.full_like(y, mean_y, dtype=float)
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }

        x1 = X[:, 0]
        x2 = X[:, 1]

        B, basis_exprs = self._build_basis(x1, x2)
        n_basis = B.shape[1]

        # Orthogonal Matching Pursuit-like selection
        norms2 = np.sum(B * B, axis=0)
        used = np.zeros(n_basis, dtype=bool)

        # Always start with constant term (index 0)
        selected_idx = [0]
        used[0] = True

        B_sel = B[:, selected_idx]
        w_current, _, _, _ = np.linalg.lstsq(B_sel, y, rcond=None)
        residual = y - B_sel @ w_current
        best_mse = float(np.mean(residual ** 2))

        target_mse = max(1e-10, var_y * 1e-4)

        max_additional = max(self.max_terms - 1, 0)

        for _ in range(max_additional):
            # Compute scores as squared correlation normalized by column norm
            c = B.T @ residual  # shape (n_basis,)
            scores = (c * c) / (norms2 + 1e-12)
            scores[used | (norms2 <= 1e-12)] = -np.inf

            j_best = int(np.argmax(scores))
            if not np.isfinite(scores[j_best]) or scores[j_best] <= 0.0:
                break

            used[j_best] = True
            selected_idx.append(j_best)

            B_sel = B[:, selected_idx]
            w_new, _, _, _ = np.linalg.lstsq(B_sel, y, rcond=None)
            residual = y - B_sel @ w_new
            mse_new = float(np.mean(residual ** 2))

            w_current = w_new
            best_mse = mse_new

            if best_mse <= target_mse:
                break

        # Prune terms with very small contribution (except constant)
        std_y = float(np.std(y))
        scale = std_y if std_y > 1e-12 else 1.0
        keep_positions = []

        for pos, j in enumerate(selected_idx):
            wj = float(w_current[pos])
            if j == 0:
                # Always keep constant term; it doesn't add binary/unary ops by itself
                keep_positions.append(pos)
                continue
            contrib = B[:, j] * wj
            rms = float(np.sqrt(np.mean(contrib * contrib)))
            if rms >= 1e-3 * scale:
                keep_positions.append(pos)

        if len(keep_positions) < len(selected_idx):
            new_selected_idx = [selected_idx[pos] for pos in keep_positions]
            if len(new_selected_idx) > 0:
                B_sel = B[:, new_selected_idx]
                w_current, _, _, _ = np.linalg.lstsq(B_sel, y, rcond=None)
                selected_idx = new_selected_idx
            else:
                # Fallback to constant model if all pruned
                expression = self._format_float(mean_y)
                predictions = np.full_like(y, mean_y, dtype=float)
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {}
                }

        # Build expression string from selected basis and coefficients
        terms = []
        B_sel_final = B[:, selected_idx]
        w_current = np.asarray(w_current, dtype=float)

        for pos, j in enumerate(selected_idx):
            wj = float(w_current[pos])
            if abs(wj) < 1e-12:
                continue

            basis_expr = basis_exprs[j]

            # Constant term
            if basis_expr == "1.0":
                term_str = self._format_float(wj)
                # Skip exact zero constants
                if term_str in ("0", "0.0", "0.000000000000"):
                    continue
            else:
                if abs(wj - 1.0) < 1e-8:
                    term_str = basis_expr
                elif abs(wj + 1.0) < 1e-8:
                    term_str = f"-({basis_expr})"
                else:
                    coeff_str = self._format_float(wj)
                    term_str = f"{coeff_str}*({basis_expr})"
            terms.append(term_str)

        if not terms:
            # If everything was pruned, use constant mean
            expression = self._format_float(mean_y)
            predictions = np.full_like(y, mean_y, dtype=float)
        else:
            expr = terms[0]
            for t in terms[1:]:
                if t.startswith("-"):
                    expr += " - " + t[1:]
                else:
                    expr += " + " + t
            expression = expr
            predictions = B_sel_final @ w_current

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
