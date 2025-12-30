import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.max_base_terms = kwargs.get("max_base_terms", 8)
        self.max_phi_terms = kwargs.get("max_phi_terms", 10)
        self.alpha = kwargs.get("alpha", 1e-8)
        self.random_state = kwargs.get("random_state", 42)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, d = X.shape
        if d != 4:
            # Fallback: simple linear model if dimensions unexpected
            return self._simple_linear_solution(X, y)

        # Standard deviations for scaling; avoid zeros
        scales = np.std(X, axis=0)
        scales = np.where(scales <= 1e-12, 1.0, scales)

        # Build base polynomial (degree <= 2) monomials
        A_base, base_terms = self._build_base_features(X)

        # Candidates for exponential damping over scaled radius r2 = sum((xi/si)^2)
        # r2 has expected scale ~ number of dimensions (4), so s in [0.125, 2.0] is reasonable.
        s_candidates = [None, 0.125, 0.25, 0.5, 1.0, 2.0]

        best = None
        y_mean = np.mean(y)
        y_centered = y - y_mean

        for s in s_candidates:
            if s is None:
                A = A_base
            else:
                r2 = np.sum((X / scales) ** 2, axis=1)
                phi = np.exp(-s * r2)
                A_phi = A_base * phi[:, None]
                A = np.hstack([A_base, A_phi])

            # Ridge regression
            w_ridge = self._ridge_regression(A, y_centered, self.alpha)

            # MSE
            preds = A @ w_ridge + y_mean
            mse = np.mean((y - preds) ** 2)

            best = self._update_best(best, mse, s, w_ridge, A_base, base_terms, X, y_centered, y_mean, scales)

        # After finding best s, perform feature selection and final refit
        if best["s"] is None:
            # No exponential, only base terms
            A_base = best["A_base"]
            base_terms = best["base_terms"]
            w_ridge = best["w"]
            # Select top-K base features
            base_idx = self._select_top_k(A_base, w_ridge, k=min(self.max_base_terms, A_base.shape[1]))
            # Ensure constant term (index 0) included
            if 0 not in base_idx:
                base_idx = np.unique(np.r_[0, base_idx])
            A_sel = A_base[:, base_idx]
            w_final = self._least_squares(A_sel, y_centered)
            preds = A_sel @ w_final + y_mean
            expr = self._build_expression_no_phi(base_terms, base_idx, w_final, y_mean)
        else:
            s = best["s"]
            A_base = best["A_base"]
            base_terms = best["base_terms"]
            r2 = np.sum((X / scales) ** 2, axis=1)
            phi_vec = np.exp(-s * r2)
            A_phi = A_base * phi_vec[:, None]

            # Split weights into base and phi parts from ridge solution
            w = best["w"]
            w_base = w[:A_base.shape[1]]
            w_phi = w[A_base.shape[1]:]

            # Select top-K base and phi features
            base_idx = self._select_top_k(A_base, w_base, k=min(self.max_base_terms, A_base.shape[1]))
            phi_idx = self._select_top_k(A_phi, w_phi, k=min(self.max_phi_terms, A_phi.shape[1]))

            # Ensure constant term included in both when beneficial
            if 0 not in base_idx:
                base_idx = np.unique(np.r_[0, base_idx])
            if 0 not in phi_idx:
                phi_idx = np.unique(np.r_[0, phi_idx])

            # Refit least squares on selected features
            A_sel = np.hstack([A_base[:, base_idx], A_phi[:, phi_idx]])
            w_final = self._least_squares(A_sel, y_centered)
            preds = A_sel @ w_final + y_mean

            # Split final weights
            w_base_final = w_final[:len(base_idx)]
            w_phi_final = w_final[len(base_idx):]

            expr = self._build_expression_with_phi(
                base_terms=base_terms,
                base_idx=base_idx,
                w_base=w_base_final,
                phi_terms=base_terms,
                phi_idx=phi_idx,
                w_phi=w_phi_final,
                y_mean=y_mean,
                s=s,
                scales=scales
            )

        return {
            "expression": expr,
            "predictions": preds.tolist(),
            "details": {}
        }

    def _simple_linear_solution(self, X, y):
        n = X.shape[0]
        A = np.column_stack([X, np.ones(n)])
        w, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c, d, e = w
        expr = (
            f"{self._fmt(a)}*x1 + {self._fmt(b)}*x2 + {self._fmt(c)}*x3 + {self._fmt(d)}*x4 + {self._fmt(e)}"
        )
        preds = A @ w
        return {
            "expression": expr,
            "predictions": preds.tolist(),
            "details": {}
        }

    def _build_base_features(self, X):
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        cols = []
        terms = []

        # Constant
        cols.append(np.ones_like(x1))
        terms.append("1")

        # Linear
        cols.extend([x1, x2, x3, x4])
        terms.extend(["x1", "x2", "x3", "x4"])

        # Pairwise products
        cross_pairs = [
            (x1 * x2, "x1*x2"),
            (x1 * x3, "x1*x3"),
            (x1 * x4, "x1*x4"),
            (x2 * x3, "x2*x3"),
            (x2 * x4, "x2*x4"),
            (x3 * x4, "x3*x4"),
        ]
        for col, name in cross_pairs:
            cols.append(col)
            terms.append(name)

        # Squares
        squares = [
            (x1 * x1, "x1**2"),
            (x2 * x2, "x2**2"),
            (x3 * x3, "x3**2"),
            (x4 * x4, "x4**2"),
        ]
        for col, name in squares:
            cols.append(col)
            terms.append(name)

        A = np.column_stack(cols)
        return A, terms

    def _ridge_regression(self, A, y, alpha):
        AtA = A.T @ A
        n_features = AtA.shape[0]
        reg = alpha * np.eye(n_features)
        try:
            w = np.linalg.solve(AtA + reg, A.T @ y)
        except np.linalg.LinAlgError:
            # Fallback to least squares if singular
            w, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        return w

    def _least_squares(self, A, y):
        w, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        return w

    def _update_best(self, best, mse, s, w, A_base, base_terms, X, y_centered, y_mean, scales):
        if best is None or mse < best["mse"]:
            return {
                "mse": mse,
                "s": s,
                "w": w,
                "A_base": A_base,
                "base_terms": base_terms,
                "X": X,
                "y_centered": y_centered,
                "y_mean": y_mean,
                "scales": scales,
            }
        return best

    def _select_top_k(self, A, w, k):
        # Importance based on absolute contribution: |w| * std(col)
        stds = np.std(A, axis=0)
        importance = np.abs(w) * (stds + 1e-12)
        # Always consider absolute coefficients even if std is zero (constant)
        importance = np.where(stds <= 1e-18, np.abs(w), importance)
        idx_sorted = np.argsort(-importance)
        k = max(1, min(k, A.shape[1]))
        return np.sort(idx_sorted[:k])

    def _fmt(self, v):
        if not np.isfinite(v):
            return "0"
        if abs(v) < 1e-14:
            return "0"
        return format(float(v), ".12g")

    def _combine_terms(self, coeffs, terms):
        # terms: list of strings, same length as coeffs
        # Build an expression string with proper +/-
        expr = ""
        first = True
        for c, t in zip(coeffs, terms):
            if abs(c) < 1e-14:
                continue
            c_abs = self._fmt(abs(c))
            if t == "1":
                term_str = f"{c_abs}"
            else:
                term_str = f"{c_abs}*{t}"
            if first:
                if c < 0:
                    expr = "-" + term_str
                else:
                    expr = term_str
                first = False
            else:
                if c < 0:
                    expr += " - " + term_str
                else:
                    expr += " + " + term_str
        if expr == "":
            expr = "0"
        return expr

    def _phi_str(self, s, scales):
        s1 = self._fmt(scales[0])
        s2 = self._fmt(scales[1])
        s3 = self._fmt(scales[2])
        s4 = self._fmt(scales[3])
        s_const = self._fmt(s)
        r2 = f"((x1/{s1})**2 + (x2/{s2})**2 + (x3/{s3})**2 + (x4/{s4})**2)"
        return f"exp(-{s_const}*{r2})"

    def _build_expression_no_phi(self, base_terms, base_idx, w_base, y_mean):
        # Build base polynomial expression plus intercept y_mean
        # Terms: base_idx maps into base_terms and w_base
        selected_terms = [base_terms[i] for i in base_idx]
        expr_poly = self._combine_terms(w_base, selected_terms)
        intercept = self._fmt(y_mean)
        if expr_poly == "0":
            return f"{intercept}"
        if intercept == "0":
            return expr_poly
        # Combine with intercept
        if intercept.startswith("-"):
            return f"{expr_poly} - {self._fmt(abs(float(intercept)))}"
        else:
            return f"{expr_poly} + {intercept}"

    def _build_expression_with_phi(self, base_terms, base_idx, w_base, phi_terms, phi_idx, w_phi, y_mean, s, scales):
        # Build base polynomial
        base_selected = [base_terms[i] for i in base_idx]
        expr_base = self._combine_terms(w_base, base_selected)

        # Build inner polynomial for phi
        phi_selected = [phi_terms[i] for i in phi_idx]
        expr_inner = self._combine_terms(w_phi, phi_selected)

        phi = self._phi_str(s, scales)
        # Build final expression: base + (inner) * phi + y_mean
        # Start with intercept
        intercept = self._fmt(y_mean)

        parts = []

        if expr_base != "0":
            parts.append(expr_base)

        if expr_inner != "0":
            parts.append(f"({expr_inner})*{phi}")

        if not parts:
            # Both zero: return just intercept
            return f"{intercept}"

        expr = parts[0]
        for p in parts[1:]:
            # Add with plus
            expr = f"{expr} + {p}"

        # Add intercept
        if intercept != "0":
            if intercept.startswith("-"):
                expr = f"{expr} - {self._fmt(abs(float(intercept)))}"
            else:
                expr = f"{expr} + {intercept}"

        return expr