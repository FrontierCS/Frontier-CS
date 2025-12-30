import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = kwargs.get("random_state", 42)
        self.max_passes = kwargs.get("max_passes", 12)
        self.b_clip = kwargs.get("b_clip", (0.0, 10.0))
        self.subsample_size = kwargs.get("subsample_size", 4000)
        self.scale_factors = kwargs.get("scale_factors", [0.5, 0.7, 0.9, 1.1, 1.4, 2.0])
        self.abs_candidates = kwargs.get("abs_candidates", [0.0, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0])
        self.init_b_values = kwargs.get("init_b_values", [0.0, 0.1, 0.3, 0.5, 1.0, 2.0])

    def _build_features(self, X):
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]
        ones = np.ones_like(x1)
        x1_2 = x1 * x1
        x2_2 = x2 * x2
        x3_2 = x3 * x3
        x4_2 = x4 * x4

        # Order: [1, x1, x2, x3, x4, x1^2, x2^2, x3^2, x4^2, x1x2, x1x3, x1x4, x2x3, x2x4, x3x4]
        psi = np.column_stack([
            ones,
            x1, x2, x3, x4,
            x1_2, x2_2, x3_2, x4_2,
            x1 * x2, x1 * x3, x1 * x4,
            x2 * x3, x2 * x4, x3 * x4,
        ])
        monoms = [
            "1",
            "x1", "x2", "x3", "x4",
            "x1**2", "x2**2", "x3**2", "x4**2",
            "x1*x2", "x1*x3", "x1*x4",
            "x2*x3", "x2*x4", "x3*x4",
        ]
        X2 = np.column_stack([x1_2, x2_2, x3_2, x4_2])
        return psi, monoms, X2

    def _fit_given_b(self, psi, X2, y, b):
        g = np.exp(-X2.dot(b))
        H = psi * g[:, None]
        # lstsq for stability
        a, _, _, _ = np.linalg.lstsq(H, y, rcond=None)
        pred = H.dot(a)
        mse = np.mean((y - pred) ** 2)
        return a, mse, pred, g

    def _coordinate_search(self, psi, X2, y, b_start):
        b = np.array(b_start, dtype=float).copy()
        b = np.clip(b, self.b_clip[0], self.b_clip[1])
        best_a, best_mse, _, _ = self._fit_given_b(psi, X2, y, b)
        improved_global = True
        passes = 0
        while improved_global and passes < self.max_passes:
            improved_global = False
            passes += 1
            for j in range(4):
                current_bj = b[j]
                best_local_mse = best_mse
                best_local_bj = current_bj
                # Prepare candidate list
                cand_vals = []
                for s in self.scale_factors:
                    cand_vals.append(current_bj * s)
                cand_vals.extend(self.abs_candidates)
                # Clip and deduplicate candidates
                cand_vals = [min(max(v, self.b_clip[0]), self.b_clip[1]) for v in cand_vals]
                cand_vals = np.unique(np.array(cand_vals))
                for cand in cand_vals:
                    if abs(cand - current_bj) < 1e-12:
                        continue
                    b_try = b.copy()
                    b_try[j] = cand
                    a_try, mse_try, _, _ = self._fit_given_b(psi, X2, y, b_try)
                    if mse_try + 1e-12 < best_local_mse:
                        best_local_mse = mse_try
                        best_local_bj = cand
                        best_a = a_try
                if best_local_mse + 1e-12 < best_mse:
                    b[j] = best_local_bj
                    best_mse = best_local_mse
                    improved_global = True
        # Final fit with best b
        best_a, best_mse, _, _ = self._fit_given_b(psi, X2, y, b)
        return b, best_a, best_mse

    def _polynomial_only(self, psi, y):
        a, _, _, _ = np.linalg.lstsq(psi, y, rcond=None)
        pred = psi.dot(a)
        mse = np.mean((y - pred) ** 2)
        return a, mse, pred

    def _threshold_and_refit(self, psi, y, X2, b, a, keep_min=1, rel_thresh=1e-3):
        # Threshold small coefficients to reduce complexity and refit using retained features
        a_abs = np.abs(a)
        max_a = np.max(a_abs) if a_abs.size > 0 else 0.0
        if max_a == 0:
            return a
        thresh = rel_thresh * max_a
        keep_idx = np.where(a_abs >= thresh)[0]
        if keep_idx.size < keep_min:
            keep_idx = np.argsort(-a_abs)[:keep_min]
        keep_idx = np.sort(keep_idx)
        g = np.exp(-X2.dot(b))
        Hk = psi[:, keep_idx] * g[:, None]
        ak, _, _, _ = np.linalg.lstsq(Hk, y, rcond=None)
        a_new = np.zeros_like(a)
        a_new[keep_idx] = ak
        return a_new

    def _build_expression(self, a, b, monoms, coeff_prec=12):
        # Build polynomial string
        def fmt(v):
            if abs(v) < 1e-14:
                v = 0.0
            s = f"{v:.{coeff_prec}g}"
            if s == "-0":
                s = "0"
            return s

        terms = []
        for coeff, m in zip(a, monoms):
            if abs(coeff) < 1e-12:
                continue
            if m == "1":
                term = fmt(coeff)
            else:
                term = f"{fmt(coeff)}*{m}"
            terms.append(term)

        if not terms:
            poly_str = "0"
        else:
            # Combine with proper signs
            poly_str = terms[0]
            for t in terms[1:]:
                if t.startswith("-"):
                    poly_str += " - " + t[1:]
                else:
                    poly_str += " + " + t

        # Build exponent string
        exp_terms = []
        xb = ["x1", "x2", "x3", "x4"]
        for bi, xi in zip(b, xb):
            if abs(bi) < 1e-14:
                continue
            exp_terms.append(f"{fmt(bi)}*{xi}**2")
        if not exp_terms:
            exponent = "0"
        else:
            expr = exp_terms[0]
            for t in exp_terms[1:]:
                if t.startswith("-"):
                    expr += " - " + t[1:]
                else:
                    expr += " + " + t
            exponent = expr

        if exponent == "0":
            expression = f"({poly_str})"
        else:
            expression = f"({poly_str})*exp(-({exponent}))"
        return expression

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        rng = np.random.default_rng(self.random_state)
        n = X.shape[0]
        psi_full, monoms, X2_full = self._build_features(X)

        # Baseline polynomial-only model
        a_poly, mse_poly, pred_poly = self._polynomial_only(psi_full, y)

        # Subsample for b search to speed up
        if n > self.subsample_size:
            idx = rng.choice(n, size=self.subsample_size, replace=False)
            psi = psi_full[idx]
            X2 = X2_full[idx]
            y_sub = y[idx]
        else:
            psi = psi_full
            X2 = X2_full
            y_sub = y

        # Try multiple initializations for b, run coordinate search, keep best
        best_b = np.zeros(4, dtype=float)
        best_a = a_poly.copy()
        best_mse = mse_poly

        for b0 in self.init_b_values:
            b_start = np.array([b0, b0, b0, b0], dtype=float)
            b_fit, a_fit, mse_fit = self._coordinate_search(psi, X2, y_sub, b_start)
            if mse_fit + 1e-12 < best_mse:
                best_mse = mse_fit
                best_b = b_fit
                best_a = a_fit

        # Refit best model on full data
        a_full, mse_full, _, _ = self._fit_given_b(psi_full, X2_full, y, best_b)

        # Optionally threshold and refit to reduce complexity
        a_full_thresh = self._threshold_and_refit(psi_full, y, X2_full, best_b, a_full, keep_min=3, rel_thresh=1e-3)
        # Evaluate after thresholding
        g_full = np.exp(-X2_full.dot(best_b))
        pred_thresh = (psi_full.dot(a_full_thresh)) * g_full
        mse_thresh = np.mean((y - pred_thresh) ** 2)

        # Compare polynomial-only vs exponential model
        final_use_poly = False
        final_a = a_full_thresh
        final_b = best_b
        final_pred = pred_thresh
        final_mse = mse_thresh

        if final_mse > mse_full + 1e-10:
            # Thresholding degraded; use non-thresholded
            final_a = a_full
            final_pred = (psi_full.dot(final_a)) * g_full
            final_mse = np.mean((y - final_pred) ** 2)

        # If exponential model is not better than polynomial-only, use polynomial-only
        if final_mse > mse_poly * 0.999 + 1e-12:
            final_use_poly = True

        if final_use_poly:
            expression = self._build_expression(a_poly, np.zeros(4), monoms)
            predictions = pred_poly
        else:
            expression = self._build_expression(final_a, final_b, monoms)
            predictions = final_pred

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }