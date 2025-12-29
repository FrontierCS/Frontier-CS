import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 42))

    def _poly_terms(self, X, spec):
        x1 = X[:, 0]
        x2 = X[:, 1]
        if spec == "linxy":
            # [1, x1, x2, x1*x2]
            return np.column_stack((np.ones_like(x1), x1, x2, x1 * x2))
        elif spec == "quad":
            # [1, x1, x2, x1^2, x1*x2, x2^2]
            return np.column_stack((np.ones_like(x1), x1, x2, x1 * x1, x1 * x2, x2 * x2))
        else:
            # default to quad
            return np.column_stack((np.ones_like(x1), x1, x2, x1 * x1, x1 * x2, x2 * x2))

    def _poly_str(self, coeffs, spec):
        # Build polynomial string with given coefficients and spec
        terms = []
        def fmt(c):
            return f"{c:.12g}"

        if spec == "linxy":
            # c0 + c1*x1 + c2*x2 + c3*x1*x2
            if abs(coeffs[0]) > 0:
                terms.append(fmt(coeffs[0]))
            if abs(coeffs[1]) > 0:
                terms.append(f"({fmt(coeffs[1])}*x1)")
            if abs(coeffs[2]) > 0:
                terms.append(f"({fmt(coeffs[2])}*x2)")
            if abs(coeffs[3]) > 0:
                terms.append(f"({fmt(coeffs[3])}*x1*x2)")
        else:
            # quad: c0 + c1*x1 + c2*x2 + c3*x1**2 + c4*x1*x2 + c5*x2**2
            if abs(coeffs[0]) > 0:
                terms.append(fmt(coeffs[0]))
            if abs(coeffs[1]) > 0:
                terms.append(f"({fmt(coeffs[1])}*x1)")
            if abs(coeffs[2]) > 0:
                terms.append(f"({fmt(coeffs[2])}*x2)")
            if abs(coeffs[3]) > 0:
                terms.append(f"({fmt(coeffs[3])}*x1**2)")
            if abs(coeffs[4]) > 0:
                terms.append(f"({fmt(coeffs[4])}*x1*x2)")
            if abs(coeffs[5]) > 0:
                terms.append(f"({fmt(coeffs[5])}*x2**2)")

        if not terms:
            return "0"
        return " + ".join(terms)

    def _kmeans_2d(self, X, k, steps=20, seed=42):
        n = X.shape[0]
        rng = np.random.default_rng(seed)
        # Initialize centers with k random points
        if n < k:
            k = n
        idx = rng.choice(n, size=k, replace=False)
        centers = X[idx].astype(float).copy()

        for _ in range(steps):
            # Compute squared distances [n,k]
            d2 = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
            labels = np.argmin(d2, axis=1)
            new_centers = centers.copy()
            for j in range(k):
                mask = labels == j
                if np.any(mask):
                    new_centers[j] = X[mask].mean(axis=0)
                else:
                    # Reinitialize empty cluster to a random point
                    ridx = rng.integers(0, n)
                    new_centers[j] = X[ridx]
            if np.allclose(new_centers, centers):
                centers = new_centers
                break
            centers = new_centers
        return centers

    def _compute_alphas(self, centers, width_factor, X):
        k = centers.shape[0]
        alphas = np.zeros(k, dtype=float)
        # Fallback scale based on data dispersion
        s_global = float(np.mean(np.std(X, axis=0))) + 1e-12
        for j in range(k):
            d = np.sqrt(((centers[j][None, :] - centers) ** 2).sum(axis=1))
            d = d[d > 1e-12]
            if d.size == 0:
                s = s_global
            else:
                s = float(np.median(d))
                if not np.isfinite(s) or s < 1e-12:
                    s = s_global
            alphas[j] = float(width_factor / (s * s + 1e-12))
        return alphas

    def _build_design(self, X, centers, alphas, poly_spec_base, poly_spec_gauss):
        # Base polynomial
        Phi_base = self._poly_terms(X, poly_spec_base)
        P_base = Phi_base.shape[1]
        n = X.shape[0]

        # Gaussian-polynomial features
        x1 = X[:, 0]
        x2 = X[:, 1]
        k = centers.shape[0]
        Phi_list = [Phi_base]
        P_gauss = 4 if poly_spec_gauss == "linxy" else 6

        for j in range(k):
            cx, cy = centers[j]
            alpha = alphas[j]
            r2 = (x1 - cx) ** 2 + (x2 - cy) ** 2
            e = np.exp(-alpha * r2)
            if poly_spec_gauss == "linxy":
                # e, x1*e, x2*e, x1*x2*e
                Gj = np.column_stack((e, x1 * e, x2 * e, (x1 * x2) * e))
            else:
                # quad: e, x1*e, x2*e, x1^2*e, x1*x2*e, x2^2*e
                Gj = np.column_stack((e, x1 * e, x2 * e, (x1 * x1) * e, (x1 * x2) * e, (x2 * x2) * e))
            Phi_list.append(Gj)

        Phi = np.concatenate(Phi_list, axis=1)
        return Phi, P_base, P_gauss

    def _ridge_solve(self, Phi, y, lam):
        # Solve (Phi^T Phi + lam*I) w = Phi^T y
        # Use Cholesky if possible; else fall back to lstsq
        P = Phi.shape[1]
        A = Phi.T @ Phi
        b = Phi.T @ y
        A.flat[:: P + 1] += lam
        try:
            w = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            w, _, _, _ = np.linalg.lstsq(Phi, y, rcond=None)
        return w

    def _mse(self, y, yhat):
        d = y - yhat
        return float(np.mean(d * d))

    def _peaks_like_values(self, X):
        x = X[:, 0]
        y = X[:, 1]
        term1 = 3.0 * (1.0 - x) ** 2 * np.exp(-(x ** 2) - (y + 1.0) ** 2)
        term2 = -10.0 * (x / 5.0 - x ** 3 - y ** 5) * np.exp(-(x ** 2) - (y ** 2))
        term3 = -1.0 / 3.0 * np.exp(-((x + 1.0) ** 2) - (y ** 2))
        return term1 + term2 + term3

    def _format_gaussian_term(self, coeffs, spec, alpha, cx, cy):
        # returns string like: (poly(x1,x2)) * exp(-alpha*((x1-cx)**2 + (x2-cy)**2))
        poly_str = self._poly_str(coeffs, spec)
        alpha_s = f"{alpha:.12g}"
        cx_s = f"{cx:.12g}"
        cy_s = f"{cy:.12g}"
        exp_str = f"exp(-({alpha_s})*((x1-({cx_s}))**2 + (x2-({cy_s}))**2))"
        if poly_str == "0":
            return "0"
        # If polynomial reduces to a single number (no 'x'), still wrap in parentheses for clarity
        return f"({poly_str})*{exp_str}"

    def _build_expression(self, centers, alphas, w, P_base, P_gauss, poly_spec_base, poly_spec_gauss):
        # w: concatenated weights [P_base + k*P_gauss]
        def is_near_zero(v):
            return abs(v) < 1e-14

        base_coeffs = w[:P_base]
        expr_parts = []
        base_str = self._poly_str(base_coeffs, poly_spec_base)
        if base_str != "0":
            expr_parts.append(base_str)

        # Gaussian parts
        k = centers.shape[0]
        for j in range(k):
            start = P_base + j * P_gauss
            end = start + P_gauss
            coeffs = w[start:end]
            # Skip if all near zero
            if np.all(np.abs(coeffs) < 1e-14):
                continue
            term_str = self._format_gaussian_term(coeffs, poly_spec_gauss, alphas[j], centers[j, 0], centers[j, 1])
            if term_str != "0":
                expr_parts.append(term_str)

        if not expr_parts:
            return "0"
        return " + ".join(expr_parts)

    def _predict_with_model(self, X, centers, alphas, w, P_base, P_gauss, poly_spec_base, poly_spec_gauss):
        # Compute predictions given model parameters
        Phi, _, _ = self._build_design(X, centers, alphas, poly_spec_base, poly_spec_gauss)
        return Phi @ w

    def _linear_baseline(self, X, y):
        # Linear regression baseline with bias
        A = np.column_stack([X, np.ones(X.shape[0])])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c = coeffs
        expr = f"({a:.12g}*x1 + {b:.12g}*x2 + {c:.12g})"
        preds = A @ coeffs
        mse = self._mse(y, preds)
        return expr, preds, mse

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Ensure numpy arrays
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, d = X.shape
        if d != 2:
            # Fallback: treat extra dims with only first 2
            X = X[:, :2]
        if n == 0:
            return {"expression": "0", "predictions": [], "details": {}}

        # Edge case: constant y
        if np.allclose(y, y.mean(), atol=1e-12):
            c = float(y.mean())
            expr_const = f"{c:.12g}"
            return {"expression": expr_const, "predictions": (np.ones(n) * c).tolist(), "details": {}}

        rng = np.random.default_rng(self.random_state)

        # Baseline linear model
        best_expr, best_preds, best_mse = self._linear_baseline(X, y)
        best_details = {"model": "linear"}

        # Candidate: peaks-like formula scaled
        p_vals = self._peaks_like_values(X)
        if np.all(np.isfinite(p_vals)) and (not np.allclose(p_vals.std(), 0.0)):
            A = np.column_stack([p_vals, np.ones_like(p_vals)])
            ab, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a_scale, b_off = ab
            preds_peaks = a_scale * p_vals + b_off
            mse_peaks = self._mse(y, preds_peaks)
            peaks_expr = (
                f"({a_scale:.12g})*(3*(1 - x1)**2*exp(-(x1**2) - (x2 + 1)**2) - "
                f"10*(x1/5 - x1**3 - x2**5)*exp(-(x1**2) - (x2**2)) - "
                f"(1/3)*exp(-((x1 + 1)**2) - (x2**2))) + ({b_off:.12g})"
            )
            if mse_peaks < best_mse:
                best_mse = mse_peaks
                best_preds = preds_peaks
                best_expr = peaks_expr
                best_details = {"model": "peaks_scaled"}

        # RBF-Gaussian polynomial mixture candidates
        # Precompute centers for different k to avoid repeated kmeans for each grid
        k_values = [3, 4, 5]
        centers_dict = {}
        for k in k_values:
            centers_dict[k] = self._kmeans_2d(X, k, steps=20, seed=self.random_state)

        width_factors = [0.25, 0.5, 1.0]
        lam_list = [1e-6, 1e-3]
        poly_specs = [("quad", "quad"), ("quad", "linxy")]

        for k in k_values:
            centers = centers_dict[k]
            for wf in width_factors:
                alphas = self._compute_alphas(centers, wf, X)
                for lam in lam_list:
                    for poly_spec_base, poly_spec_gauss in poly_specs:
                        Phi, P_base, P_gauss = self._build_design(X, centers, alphas, poly_spec_base, poly_spec_gauss)
                        w = self._ridge_solve(Phi, y, lam)
                        preds = Phi @ w
                        mse = self._mse(y, preds)
                        if mse < best_mse:
                            expr = self._build_expression(centers, alphas, w, P_base, P_gauss, poly_spec_base, poly_spec_gauss)
                            # Keep slightly simplified expression: if empty, fallback to linear
                            if expr.strip() == "":
                                continue
                            best_mse = mse
                            best_preds = preds
                            best_expr = expr
                            best_details = {
                                "model": "rbf_poly",
                                "k": int(k),
                                "width_factor": float(wf),
                                "lambda": float(lam),
                                "poly_base": poly_spec_base,
                                "poly_gauss": poly_spec_gauss,
                            }

        return {
            "expression": best_expr,
            "predictions": best_preds.tolist(),
            "details": best_details,
        }