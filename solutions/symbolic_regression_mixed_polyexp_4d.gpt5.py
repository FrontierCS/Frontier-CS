import numpy as np

class Solution:
    def __init__(self, max_terms: int = 20, alphas=None, shift_alphas=None, shift_bs=None, **kwargs):
        # Hyperparameters for feature generation and selection
        self.max_terms = int(max_terms)
        self.alphas = alphas if alphas is not None else (0.2, 0.5, 1.0, 2.0)
        self.shift_alphas = shift_alphas if shift_alphas is not None else (0.5, 1.0)
        self.shift_bs = shift_bs if shift_bs is not None else (-2.0, -1.0, 1.0, 2.0)

    def _format_float(self, x):
        s = f"{float(x):.12g}"
        # Clean up negative zero
        if s == "-0" or s == "-0.0":
            s = "0"
        return s

    def _build_polynomial_terms(self, X):
        # Returns (names, values_list)
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        x1_2 = x1 * x1
        x2_2 = x2 * x2
        x3_2 = x3 * x3
        x4_2 = x4 * x4

        x1_3 = x1_2 * x1
        x2_3 = x2_2 * x2
        x3_3 = x3_2 * x3
        x4_3 = x4_2 * x4

        names = []
        vals = []

        # Degree 1
        names.extend(["x1", "x2", "x3", "x4"])
        vals.extend([x1, x2, x3, x4])

        # Degree 2: squares and pairwise products
        names.extend(["x1**2", "x2**2", "x3**2", "x4**2"])
        vals.extend([x1_2, x2_2, x3_2, x4_2])

        names.extend([
            "x1*x2", "x1*x3", "x1*x4", "x2*x3", "x2*x4", "x3*x4"
        ])
        vals.extend([
            x1 * x2, x1 * x3, x1 * x4, x2 * x3, x2 * x4, x3 * x4
        ])

        # Degree 3: cubes
        names.extend(["x1**3", "x2**3", "x3**3", "x4**3"])
        vals.extend([x1_3, x2_3, x3_3, x4_3])

        # Degree 3: squared times other variable
        for i_name, i_sq in [("x1", x1_2), ("x2", x2_2), ("x3", x3_2), ("x4", x4_2)]:
            for j_name, j in [("x1", x1), ("x2", x2), ("x3", x3), ("x4", x4)]:
                if i_name != j_name:
                    names.append(f"{i_name}**2*{j_name}")
                    vals.append(i_sq * j)

        # Degree 3: triple products
        names.extend([
            "x1*x2*x3", "x1*x2*x4", "x1*x3*x4", "x2*x3*x4"
        ])
        vals.extend([
            x1 * x2 * x3, x1 * x2 * x4, x1 * x3 * x4, x2 * x3 * x4
        ])

        return names, vals

    def _build_features(self, X):
        # Build a library of features: polynomials, exp(-a*r2), and polynomial*exp(-a*r2)
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        poly_names, poly_vals = self._build_polynomial_terms(X)

        names = []
        vals = []

        # Add pure polynomial terms
        names.extend(poly_names)
        vals.extend(poly_vals)

        # r2 and its expression
        r2 = x1 * x1 + x2 * x2 + x3 * x3 + x4 * x4
        r2_expr = "x1**2 + x2**2 + x3**2 + x4**2"

        # Add exp(-a*r2) and polynomial*exp(-a*r2)
        for a in self.alphas:
            ea = np.exp(-a * r2)
            a_str = self._format_float(a)
            exp_name = f"exp(-{a_str}*({r2_expr}))"
            names.append(exp_name)
            vals.append(ea)

            # Multiply by polynomials up to degree 2 for manageable size
            # We know the first 4 + 10 = 14 entries are deg1 and deg2 (from _build_polynomial_terms)
            deg1_deg2_count = 4 + 10
            for i in range(deg1_deg2_count):
                pn = poly_names[i]
                pv = poly_vals[i]
                names.append(f"({pn})*{exp_name}")
                vals.append(pv * ea)

        # Shifted exponentials: exp(-a*r2 + b*xi) for i=1..4 and b in shift_bs
        for a in self.shift_alphas:
            ea_base = -a * r2
            a_str = self._format_float(a)
            for dim, (var_name, var_val) in enumerate([("x1", x1), ("x2", x2), ("x3", x3), ("x4", x4)], start=1):
                for b in self.shift_bs:
                    b_str = self._format_float(b)
                    # Construct name with explicit + or - for b*xi
                    if b >= 0:
                        exp_name = f"exp(-{a_str}*({r2_expr}) + {b_str}*{var_name})"
                    else:
                        exp_name = f"exp(-{a_str}*({r2_expr}) - {self._format_float(-b)}*{var_name})"
                    names.append(exp_name)
                    vals.append(np.exp(ea_base + b * var_val))

        # Remove duplicate features by name (should not occur but safeguard)
        unique_names = []
        unique_vals = []
        seen = set()
        for nm, vl in zip(names, vals):
            if nm not in seen:
                seen.add(nm)
                unique_names.append(nm)
                unique_vals.append(vl)

        # Stack into matrix
        F = np.column_stack(unique_vals) if unique_vals else np.zeros((n, 0), dtype=float)
        return unique_names, F

    def _omp_select(self, F, y, max_terms):
        # Orthogonal Matching Pursuit on centered+normalized features with intercept
        n, k = F.shape
        if k == 0:
            return []

        # Center features
        means = F.mean(axis=0)
        S = F - means

        # Norms for normalization
        norms = np.sqrt(np.sum(S * S, axis=0))
        valid = norms > 1e-12
        if not np.any(valid):
            return []

        # Filter to valid
        S = S[:, valid]
        F_valid = F[:, valid]
        norms = norms[valid]
        k_valid = S.shape[1]
        idx_map = np.where(valid)[0]

        # Initialize
        y = y.astype(float)
        ones = np.ones(n, dtype=float)
        r = y - y.mean()
        rss_prev = np.dot(r, r)
        selected_local = []
        used = np.zeros(k_valid, dtype=bool)

        max_iter = max_terms
        for _ in range(max_iter):
            # Compute correlations with normalized features: Z = S / norms
            # scores = Z.T @ r
            scores = (S.T @ r) / norms
            # Exclude used
            if used.any():
                scores = scores.copy()
                scores[used] = 0.0

            j = int(np.argmax(np.abs(scores)))
            best_corr = float(np.abs(scores[j]))
            if not np.isfinite(best_corr) or best_corr < 1e-10:
                break

            used[j] = True
            selected_local.append(j)

            # Build normalized selected design Z_sel
            Z_sel = S[:, selected_local] / norms[selected_local]
            A = np.column_stack([ones, Z_sel])

            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            r = y - A @ coef
            rss_new = np.dot(r, r)
            # Stop if improvement is tiny
            if rss_prev - rss_new < 1e-8 * max(rss_prev, 1.0):
                break
            rss_prev = rss_new

        # Map back to original indices
        selected_original = [int(idx_map[j]) for j in selected_local]
        return selected_original

    def _fit_final(self, F, y, selected_idx):
        n = F.shape[0]
        ones = np.ones(n, dtype=float)
        if len(selected_idx) == 0:
            # Only intercept
            coef0 = float(np.mean(y))
            return coef0, np.array([]), np.array([], dtype=int)

        X_sel = F[:, selected_idx]
        A = np.column_stack([ones, X_sel])
        coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        coef0 = float(coef[0])
        coefs = coef[1:]

        # Prune very small coefficients
        abs_coefs = np.abs(coefs)
        if abs_coefs.size > 0:
            thresh = 1e-8 * (np.linalg.norm(y) / np.sqrt(max(len(y), 1)))
            keep_mask = abs_coefs > thresh
            if not np.any(keep_mask):
                # Keep the largest magnitude term if all pruned
                max_idx = int(np.argmax(abs_coefs))
                keep_mask = np.zeros_like(abs_coefs, dtype=bool)
                keep_mask[max_idx] = True
            keep_idx = np.where(keep_mask)[0]
            selected_idx = [selected_idx[i] for i in keep_idx]
            X_sel = F[:, selected_idx]
            A = np.column_stack([ones, X_sel])
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            coef0 = float(coef[0])
            coefs = coef[1:]
        return coef0, coefs, np.array(selected_idx, dtype=int)

    def _build_expression(self, coef0, coefs, selected_idx, names):
        # Build expression string from coefficients and selected feature names
        parts = []
        # Intercept
        if abs(coef0) > 1e-12 or (coefs.size == 0):
            parts.append(self._format_float(coef0))

        # Add terms
        for c, idx in zip(coefs, selected_idx):
            name = names[int(idx)]
            c_abs = abs(float(c))
            if c_abs <= 1e-12:
                continue
            c_str = self._format_float(c_abs)
            term = f"{c_str}*({name})"
            if c >= 0:
                parts.append(f"+ {term}")
            else:
                parts.append(f"- {term}")

        if not parts:
            return "0"
        # Join and clean leading "+ "
        expr = " ".join(parts)
        expr = expr.replace("+ -", "- ")
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, d = X.shape
        if d != 4:
            # Attempt to handle unexpected input gracefully by slicing to first 4 columns
            X = X[:, :4]

        names, F = self._build_features(X)

        # Select features via OMP
        selected_idx = self._omp_select(F, y, max_terms=self.max_terms)

        # Final fit on selected features (with intercept)
        coef0, coefs, selected_idx = self._fit_final(F, y, selected_idx)

        # Build expression
        expression = self._build_expression(coef0, coefs, selected_idx, names)

        # Predictions
        if selected_idx.size > 0:
            A = np.column_stack([np.ones(X.shape[0], dtype=float), F[:, selected_idx]])
            coef_full = np.concatenate(([coef0], coefs))
            preds = A @ coef_full
        else:
            preds = np.full(X.shape[0], coef0, dtype=float)

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }
