import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.rel_coef_threshold = kwargs.get("rel_coef_threshold", 1e-4)
        self.abs_coef_threshold = kwargs.get("abs_coef_threshold", 1e-10)
        self.coord_passes = kwargs.get("coord_passes", 2)
        self.multipliers = kwargs.get("multipliers", [0.0, 0.0625, 0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 16.0])
        self.include_offset_options = kwargs.get("include_offset_options", [False, True])

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        n, d = X.shape
        if d != 4:
            X = X[:, :4] if d > 4 else np.pad(X, ((0, 0), (0, 4 - d)), mode="constant")
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]

        phi, term_strs = self._build_poly_features(x1, x2, x3, x4)  # NxM
        r2 = x1 * x1 + x2 * x2 + x3 * x3 + x4 * x4
        r2_mean = float(np.mean(r2) + 1e-12)
        r2_max = float(np.max(r2) + 1e-12)

        # Max lambda to avoid exp underflow (exp(-u) ~ 0 for u>700)
        lam_upper_iso = 0.9 * 690.0 / r2_max

        xi2_means = np.array([np.mean(x1 * x1) + 1e-12,
                              np.mean(x2 * x2) + 1e-12,
                              np.mean(x3 * x3) + 1e-12,
                              np.mean(x4 * x4) + 1e-12], dtype=float)
        xi2_max = np.array([np.max(x1 * x1) + 1e-12,
                            np.max(x2 * x2) + 1e-12,
                            np.max(x3 * x3) + 1e-12,
                            np.max(x4 * x4) + 1e-12], dtype=float)
        lam_upper_aniso = 0.9 * 690.0 / xi2_max

        # Baseline: polynomial only (equiv. lambda=0, no offset)
        best = {
            "mse": np.inf,
            "coefs": None,
            "offset": 0.0,
            "lams": np.zeros(4, dtype=float),
            "include_offset": False,
        }

        # Isotropic scan
        lam_iso_list = []
        for m in self.multipliers:
            lam = m / r2_mean
            lam = min(lam, lam_upper_iso)
            if lam < 0:
                lam = 0.0
            lam_iso_list.append(lam)
        lam_iso_list = np.unique(np.array(lam_iso_list, dtype=float))

        tested = set()

        for lam in lam_iso_list:
            lams = np.array([lam, lam, lam, lam], dtype=float)
            key = tuple(np.round(lams, 12))
            if key in tested:
                continue
            for include_offset in self.include_offset_options:
                res = self._fit_with_lams(phi, y, X, lams, include_offset)
                if res["mse"] < best["mse"] - 1e-12 or (abs(res["mse"] - best["mse"]) <= 1e-12 and self._is_simpler(res, best)):
                    best = res
            tested.add(key)

        # Anisotropic coordinate descent
        lams = np.zeros(4, dtype=float)
        current_best_mse = np.inf
        for _ in range(self.coord_passes):
            improved = False
            for i in range(4):
                cand_lams = []
                for m in self.multipliers:
                    lam_i = m / xi2_means[i]
                    lam_i = min(lam_i, lam_upper_aniso[i])
                    if lam_i < 0:
                        lam_i = 0.0
                    cand_lams.append(lam_i)
                cand_lams = np.unique(np.array(cand_lams, dtype=float))

                local_best = None
                for lam_i in cand_lams:
                    lams_try = lams.copy()
                    lams_try[i] = lam_i
                    key = tuple(np.round(lams_try, 12))
                    if key in tested:
                        continue
                    for include_offset in self.include_offset_options:
                        res = self._fit_with_lams(phi, y, X, lams_try, include_offset)
                        if (local_best is None) or (res["mse"] < local_best["mse"] - 1e-12) or (abs(res["mse"] - local_best["mse"]) <= 1e-12 and self._is_simpler(res, local_best)):
                            local_best = res
                    tested.add(key)
                if local_best is not None and local_best["mse"] < current_best_mse - 1e-12:
                    lams = local_best["lams"]
                    current_best_mse = local_best["mse"]
                    if local_best["mse"] < best["mse"] - 1e-12 or (abs(local_best["mse"] - best["mse"]) <= 1e-12 and self._is_simpler(local_best, best)):
                        best = local_best
                    improved = True
            if not improved:
                break

        # Also include strict polynomial-only (k=0) evaluation (ensure tested)
        lams_zero = np.zeros(4, dtype=float)
        for include_offset in [False, True]:
            res = self._fit_with_lams(phi, y, X, lams_zero, include_offset)
            if res["mse"] < best["mse"] - 1e-12 or (abs(res["mse"] - best["mse"]) <= 1e-12 and self._is_simpler(res, best)):
                best = res

        # Build final expression string with sparsification
        expression = self._build_expression_string(best["coefs"], best["offset"], best["lams"], term_strs)

        # Predictions
        predictions = self._predict_from_params(X, phi, best["coefs"], best["offset"], best["lams"])

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }

    def _build_poly_features(self, x1, x2, x3, x4):
        n = x1.shape[0]
        ones = np.ones(n, dtype=float)
        terms = []

        # Constant
        cols = [ones]
        terms.append("1")

        # Linear terms
        cols.extend([x1, x2, x3, x4])
        terms.extend(["x1", "x2", "x3", "x4"])

        # Pairwise products
        cols.extend([x1 * x2, x1 * x3, x1 * x4, x2 * x3, x2 * x4, x3 * x4])
        terms.extend(["x1*x2", "x1*x3", "x1*x4", "x2*x3", "x2*x4", "x3*x4"])

        # Squared terms
        cols.extend([x1 * x1, x2 * x2, x3 * x3, x4 * x4])
        terms.extend(["x1**2", "x2**2", "x3**2", "x4**2"])

        phi = np.column_stack(cols)
        return phi, terms

    def _fit_with_lams(self, phi, y, X, lams, include_offset):
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        exp_arg = -(lams[0] * x1 * x1 + lams[1] * x2 * x2 + lams[2] * x3 * x3 + lams[3] * x4 * x4)
        # Avoid infs
        exp_arg = np.clip(exp_arg, -1e6, 1e6)
        w = np.exp(exp_arg)
        Aw = phi * w[:, None]
        if include_offset:
            A = np.column_stack([Aw, np.ones_like(y)])
        else:
            A = Aw

        # Least squares fit
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except np.linalg.LinAlgError:
            coeffs = np.zeros(A.shape[1], dtype=float)

        if include_offset:
            poly_coefs = coeffs[:-1]
            offset = float(coeffs[-1])
        else:
            poly_coefs = coeffs
            offset = 0.0

        y_pred = Aw.dot(poly_coefs) + offset
        mse = float(np.mean((y - y_pred) ** 2))

        return {
            "mse": mse,
            "coefs": poly_coefs,
            "offset": offset,
            "lams": np.array(lams, dtype=float),
            "include_offset": include_offset,
        }

    def _is_simpler(self, res_new, res_old):
        # Prefer fewer nonzero coefficients in polynomial, then fewer nonzero lambdas, then smaller absolute values sum
        count_nonzero_new = np.count_nonzero(np.abs(res_new["coefs"]) > 1e-12)
        count_nonzero_old = np.count_nonzero(np.abs(res_old["coefs"]) > 1e-12)
        if count_nonzero_new != count_nonzero_old:
            return count_nonzero_new < count_nonzero_old
        lam_nz_new = np.count_nonzero(np.abs(res_new["lams"]) > 1e-12)
        lam_nz_old = np.count_nonzero(np.abs(res_old["lams"]) > 1e-12)
        if lam_nz_new != lam_nz_old:
            return lam_nz_new < lam_nz_old
        sum_abs_new = float(np.sum(np.abs(res_new["coefs"]))) + float(np.sum(np.abs(res_new["lams"])))
        sum_abs_old = float(np.sum(np.abs(res_old["coefs"]))) + float(np.sum(np.abs(res_old["lams"])))
        return sum_abs_new < sum_abs_old

    def _format_number(self, v):
        if not np.isfinite(v):
            v = 0.0
        return f"{float(v):.12g}"

    def _build_expression_string(self, coefs, offset, lams, term_strs):
        # Sparsify coefficients
        abs_coefs = np.abs(coefs)
        max_abs = float(np.max(abs_coefs)) if abs_coefs.size > 0 else 0.0
        thr = max(self.abs_coef_threshold, self.rel_coef_threshold * max_abs)

        poly_terms = []
        for c, t in zip(coefs, term_strs):
            if abs(c) < thr:
                continue
            if t == "1":
                poly_terms.append(self._format_number(c))
            else:
                coef_str = self._format_number(c)
                poly_terms.append(f"{coef_str}*{t}")

        if len(poly_terms) == 0:
            poly_str = "0"
        else:
            # Build with correct signs
            poly_str = poly_terms[0]
            for term in poly_terms[1:]:
                if term.lstrip().startswith("-"):
                    poly_str += " - " + term.lstrip()[1:]
                else:
                    poly_str += " + " + term

        lam_thr = 1e-14
        lam_items = []
        if abs(lams[0]) > lam_thr:
            lam_items.append(f"{self._format_number(lams[0])}*x1**2")
        if abs(lams[1]) > lam_thr:
            lam_items.append(f"{self._format_number(lams[1])}*x2**2")
        if abs(lams[2]) > lam_thr:
            lam_items.append(f"{self._format_number(lams[2])}*x3**2")
        if abs(lams[3]) > lam_thr:
            lam_items.append(f"{self._format_number(lams[3])}*x4**2")

        if len(lam_items) > 0:
            exp_inner = lam_items[0]
            for term in lam_items[1:]:
                exp_inner += " + " + term
            gaussian = f"exp(-({exp_inner}))"
            expr = f"{gaussian}*({poly_str})"
        else:
            expr = f"({poly_str})"

        if abs(offset) > self.abs_coef_threshold:
            off_str = self._format_number(offset)
            if off_str.startswith("-"):
                expr = f"{expr} - {off_str[1:]}"
            else:
                expr = f"{expr} + {off_str}"

        # Clean parentheses if possible
        return expr

    def _predict_from_params(self, X, phi, coefs, offset, lams):
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        exp_arg = -(lams[0] * x1 * x1 + lams[1] * x2 * x2 + lams[2] * x3 * x3 + lams[3] * x4 * x4)
        exp_arg = np.clip(exp_arg, -1e6, 1e6)
        w = np.exp(exp_arg)
        return phi.dot(coefs) * w + offset
