import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.config = {
            "coarse_points": 36,
            "fine_points": 32,
            "cycles_min": 1.0,
            "cycles_max": 25.0,
            "w_min_abs": 0.5,
            "w_max_abs": 200.0,
            "ridge_alpha": 1e-12,
            "ds_candidates": [1, 2, 3],
            "dp_candidates": [0, 1, 2],
            "coef_threshold_scale": 1e-6,
            "harmonic_try": True,
            "harmonic_improve_ratio": 0.985,
            "random_state": None,
        }
        # Allow overrides via kwargs
        for k, v in kwargs.items():
            if k in self.config:
                self.config[k] = v

    def _ridge_fit(self, F, y, alpha=1e-12):
        M = F.shape[1]
        A = F.T @ F
        b = F.T @ y
        if alpha > 0:
            A = A + alpha * np.eye(M)
        try:
            theta = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            theta, _, _, _ = np.linalg.lstsq(F, y, rcond=None)
        yhat = F @ theta
        mse = np.mean((y - yhat) ** 2)
        return theta, yhat, mse

    def _build_features(self, r, w, dsin, dcos, dpoly):
        n = r.shape[0]
        s = np.sin(w * r)
        c = np.cos(w * r)
        ones = np.ones_like(r)
        # Precompute powers up to max degree
        dmax = max(dsin, dcos, dpoly)
        rpows = [ones]
        if dmax >= 1:
            rpows.append(r)
        if dmax >= 2:
            rpows.append(r * r)
        if dmax >= 3:
            rpows.append(rpows[2] * r)  # r^3
        if dmax >= 4:
            rpows.append(rpows[3] * r)  # r^4

        cols = []
        # sin block
        sin_idx_start = 0
        for k in range(dsin + 1):
            cols.append(rpows[k] * s)
        sin_idx_end = len(cols)
        # cos block
        for k in range(dcos + 1):
            cols.append(rpows[k] * c)
        cos_idx_end = len(cols)
        # polynomial drift block
        for k in range(dpoly + 1):
            cols.append(rpows[k])
        drift_idx_end = len(cols)

        F = np.column_stack(cols)
        idx = {
            "sin": (sin_idx_start, sin_idx_end),
            "cos": (sin_idx_end, cos_idx_end),
            "drift": (cos_idx_end, drift_idx_end),
        }
        return F, idx

    def _fit_for_w(self, r, y, w, dsin=1, dcos=1, dpoly=1, alpha=1e-12):
        F, idx = self._build_features(r, w, dsin, dcos, dpoly)
        theta, yhat, mse = self._ridge_fit(F, y, alpha=alpha)
        s0, s1 = idx["sin"]
        c0, c1 = idx["cos"]
        d0, d1 = idx["drift"]
        sin_coefs = theta[s0:s1]
        cos_coefs = theta[c0:c1]
        drift_coefs = theta[d0:d1]
        return {
            "theta": theta,
            "yhat": yhat,
            "mse": mse,
            "sin_coefs": sin_coefs,
            "cos_coefs": cos_coefs,
            "drift_coefs": drift_coefs,
        }

    def _scan_w(self, r, y, w_grid, dsin=1, dcos=1, dpoly=1, alpha=1e-12):
        best = None
        best_w = None
        best_model = None
        for w in w_grid:
            model = self._fit_for_w(r, y, w, dsin, dcos, dpoly, alpha)
            mse = model["mse"]
            if (best is None) or (mse < best):
                best = mse
                best_w = w
                best_model = model
        return best_w, best_model

    def _generate_w_grid(self, r):
        L = float(np.max(r) - np.min(r))
        if L <= 1e-9:
            # Degenerate radius span; fallback grid
            wmin = 0.5
            wmax = 40.0
        else:
            cyc_min = float(self.config["cycles_min"])
            cyc_max = float(self.config["cycles_max"])
            wmin = 2.0 * np.pi * cyc_min / L
            wmax = 2.0 * np.pi * cyc_max / L
            wmin = max(wmin, float(self.config["w_min_abs"]))
            wmax = min(wmax, float(self.config["w_max_abs"]))
            if wmin >= wmax:
                wmin = 0.5
                wmax = 40.0
        points = int(self.config["coarse_points"])
        grid = np.linspace(wmin, wmax, points)
        return grid

    def _refine_w_grid(self, w_best, r, factor=0.25):
        # Create a local grid around w_best
        # scale step relative to w_best and r-span
        points = int(self.config["fine_points"])
        if points < 3:
            points = 3
        delta = max(0.1, abs(w_best) * factor)
        wmin = max(float(self.config["w_min_abs"]), w_best - 2.0 * delta)
        wmax = min(float(self.config["w_max_abs"]), w_best + 2.0 * delta)
        if wmax <= wmin:
            wmin = max(0.5, w_best * 0.8)
            wmax = min(200.0, w_best * 1.2)
            if wmax <= wmin:
                wmin = max(0.5, w_best - 1.0)
                wmax = min(200.0, w_best + 1.0)
        grid = np.linspace(wmin, wmax, points)
        return grid

    def _fmt(self, x):
        # Format a float with precision, strip trailing zeros
        if not np.isfinite(x):
            return "0"
        s = f"{x:.12g}"
        return s

    def _poly_to_str(self, coefs, r_str, r2_str, threshold):
        # Build polynomial string in r up to degree len(coefs)-1
        # Using r^0, r^1, r^2, r^3 -> prefer r2_str for degree 2 and r*r2_str for degree 3
        terms = []
        deg = len(coefs) - 1
        for k, a in enumerate(coefs):
            if abs(a) <= threshold:
                continue
            a_str = self._fmt(a)
            if k == 0:
                terms.append(f"{a_str}")
            elif k == 1:
                terms.append(f"{a_str}*{r_str}")
            elif k == 2:
                terms.append(f"{a_str}*{r2_str}")
            elif k == 3:
                terms.append(f"{a_str}*{r2_str}*{r_str}")
            else:
                # General fallback for higher degrees
                terms.append(f"{a_str}*({r_str})**{k}")
        if not terms:
            return None
        poly = " + ".join(terms)
        # Clean up "+ -" occurrences by replacing when joining final, handled later
        return poly

    def _build_expression(self, w, sin_coefs, cos_coefs, drift_coefs, y_scale, include_harm=None):
        # Returns expression string (factored) and a function to predict
        r2_str = "(x1**2 + x2**2)"
        r_str = f"({r2_str})**0.5"
        w_str = self._fmt(w)
        threshold = float(self.config["coef_threshold_scale"]) * (abs(y_scale) + 1e-12)

        # Build base terms
        sin_poly = self._poly_to_str(sin_coefs, r_str, r2_str, threshold)
        cos_poly = self._poly_to_str(cos_coefs, r_str, r2_str, threshold)
        drift_poly = self._poly_to_str(drift_coefs, r_str, r2_str, threshold)

        terms = []
        if sin_poly is not None:
            terms.append(f"sin({w_str}*{r_str})*({sin_poly})")
        if cos_poly is not None:
            terms.append(f"cos({w_str}*{r_str})*({cos_poly})")
        if drift_poly is not None:
            terms.append(f"({drift_poly})")

        # Include harmonic if provided
        if include_harm is not None:
            w2 = include_harm["w2"]
            sin2_coefs = include_harm["sin_coefs"]
            cos2_coefs = include_harm["cos_coefs"]
            w2_str = self._fmt(w2)
            sin2_poly = self._poly_to_str(sin2_coefs, r_str, r2_str, threshold)
            cos2_poly = self._poly_to_str(cos2_coefs, r_str, r2_str, threshold)
            if sin2_poly is not None:
                terms.append(f"sin({w2_str}*{r_str})*({sin2_poly})")
            if cos2_poly is not None:
                terms.append(f"cos({w2_str}*{r_str})*({cos2_poly})")

        if not terms:
            # Fallback to zero expression
            expr = "0"
        else:
            expr = " + ".join(terms)

        return expr

    def _predict_with_coefs(self, r, w, sin_coefs, cos_coefs, drift_coefs, include_harm=None):
        # Compute predictions given the fitted coefficients (matches expression structure)
        n = r.shape[0]
        ones = np.ones_like(r)
        rpows = [ones, r, r * r, r * r * r]

        def poly_val(coefs):
            val = np.zeros(n)
            for k, a in enumerate(coefs):
                if k >= len(rpows):
                    val = val + a * (r ** k)
                else:
                    val = val + a * rpows[k]
            return val

        res = np.zeros(n)
        if sin_coefs is not None and len(sin_coefs) > 0:
            res += np.sin(w * r) * poly_val(sin_coefs)
        if cos_coefs is not None and len(cos_coefs) > 0:
            res += np.cos(w * r) * poly_val(cos_coefs)
        if drift_coefs is not None and len(drift_coefs) > 0:
            res += poly_val(drift_coefs)

        if include_harm is not None:
            w2 = include_harm["w2"]
            sin2_coefs = include_harm["sin_coefs"]
            cos2_coefs = include_harm["cos_coefs"]
            if sin2_coefs is not None and len(sin2_coefs) > 0:
                res += np.sin(w2 * r) * poly_val(sin2_coefs)
            if cos2_coefs is not None and len(cos2_coefs) > 0:
                res += np.cos(w2 * r) * poly_val(cos2_coefs)

        return res

    def _fit_harmonic(self, r, y, w_base, ds=1, alpha=1e-12):
        # Fit an additional harmonic at 2*w_base with polynomial amplitude up to degree ds
        w2 = 2.0 * w_base
        # Build feature set for harmonic only (sin and cos), plus nothing else (we'll keep base fixed)
        n = len(r)
        s2 = np.sin(w2 * r)
        c2 = np.cos(w2 * r)
        ones = np.ones_like(r)
        rpows = [ones, r, r * r, r * r * r]
        cols = []
        # sin harmonic
        for k in range(ds + 1):
            cols.append(rpows[k] * s2)
        # cos harmonic
        for k in range(ds + 1):
            cols.append(rpows[k] * c2)
        Fh = np.column_stack(cols)
        # Solve least squares: y ≈ base + Fh * beta; Equivalent to solving for beta on residuals
        # We'll return coefs for harmonic
        return Fh, w2

    def _least_squares_linear(self, X, y):
        # Simple linear regression baseline y ≈ a*x1 + b*x2 + c
        n = X.shape[0]
        A = np.column_stack([X[:, 0], X[:, 1], np.ones(n)])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        preds = A @ coeffs
        expression = f"{self._fmt(coeffs[0])}*x1 + {self._fmt(coeffs[1])}*x2 + {self._fmt(coeffs[2])}"
        return coeffs, preds, expression

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        n = X.shape[0]
        if X.ndim != 2 or X.shape[1] != 2 or y.ndim != 1 or y.shape[0] != n:
            # Fallback trivial solution
            expression = "0*x1 + 0*x2"
            return {"expression": expression, "predictions": None, "details": {}}

        x1 = X[:, 0]
        x2 = X[:, 1]
        r2 = x1 * x1 + x2 * x2
        r = np.sqrt(r2)
        y_scale = float(np.std(y)) if np.std(y) > 0 else float(np.max(np.abs(y)) + 1e-8)

        # Baseline linear model (in case ripple model fails)
        lin_coeffs, lin_preds, lin_expr = self._least_squares_linear(X, y)
        lin_mse = float(np.mean((y - lin_preds) ** 2))

        # Coarse frequency search with simple degrees
        w_grid = self._generate_w_grid(r)
        ds0, dpoly0 = 1, 1
        w_best, model_best = self._scan_w(
            r, y, w_grid, dsin=ds0, dcos=ds0, dpoly=dpoly0, alpha=self.config["ridge_alpha"]
        )

        # Fine refinement
        w_grid_fine = self._refine_w_grid(w_best, r, factor=0.3)
        w_best, model_best = self._scan_w(
            r, y, w_grid_fine, dsin=ds0, dcos=ds0, dpoly=dpoly0, alpha=self.config["ridge_alpha"]
        )

        # Try different polynomial degrees at the refined frequency and pick best by MSE (with a mild complexity penalty)
        best_combo = None
        best_score = None
        best_detail = None

        for ds in self.config["ds_candidates"]:
            for dp in self.config["dp_candidates"]:
                model = self._fit_for_w(
                    r, y, w_best, dsin=ds, dcos=ds, dpoly=dp, alpha=self.config["ridge_alpha"]
                )
                mse = model["mse"]
                # Approximate complexity: count terms; each block adds cost ~ (degree+1); factoring helps but we still penalize degrees
                complexity = (ds + 1) + (ds + 1) + (dp + 1)  # sin poly + cos poly + drift poly term counts
                # Use a mild penalty to prefer simpler models
                score = mse * (1.0 + 0.01 * complexity)
                if (best_score is None) or (score < best_score):
                    best_score = score
                    best_combo = (ds, dp)
                    best_detail = model

        ds_opt, dp_opt = best_combo
        base_model = best_detail
        base_mse = float(base_model["mse"])

        # Optionally add harmonic 2*w if it significantly improves fit
        include_harm = None
        if self.config["harmonic_try"]:
            ds_h = max(1, min(2, ds_opt))  # modest degree for harmonic
            Fh, w2 = self._fit_harmonic(r, y, w_best, ds=ds_h, alpha=self.config["ridge_alpha"])
            # Solve for harmonic coefficients on residuals of base model
            residual = y - base_model["yhat"]
            if Fh.shape[1] > 0:
                beta_h, _, _, _ = np.linalg.lstsq(Fh, residual, rcond=None)
                yhat_h = Fh @ beta_h
                mse_with_h = float(np.mean((residual - yhat_h) ** 2))
                total_mse_with_h = float(np.mean((y - (base_model["yhat"] + yhat_h)) ** 2))
                # Assess improvement
                if total_mse_with_h < base_mse * float(self.config["harmonic_improve_ratio"]):
                    # Accept harmonic
                    # Split beta_h into sin and cos parts
                    sin_h_coefs = beta_h[: ds_h + 1]
                    cos_h_coefs = beta_h[ds_h + 1 :]
                    include_harm = {
                        "w2": w2,
                        "sin_coefs": sin_h_coefs,
                        "cos_coefs": cos_h_coefs,
                    }
                    base_mse = total_mse_with_h
                else:
                    include_harm = None

        # Build expression string
        expr = self._build_expression(
            w_best,
            base_model["sin_coefs"],
            base_model["cos_coefs"],
            base_model["drift_coefs"],
            y_scale,
            include_harm=include_harm,
        )

        # Compute predictions using our coefficients
        preds = self._predict_with_coefs(
            r,
            w_best,
            base_model["sin_coefs"],
            base_model["cos_coefs"],
            base_model["drift_coefs"],
            include_harm=include_harm,
        )

        # If ripple model is worse than linear baseline, return linear baseline
        ripple_mse = float(np.mean((y - preds) ** 2))
        if ripple_mse >= lin_mse * 0.995:
            # Linear baseline is competitive or better
            return {
                "expression": lin_expr,
                "predictions": lin_preds.tolist(),
                "details": {"model": "linear", "mse": lin_mse},
            }

        return {
            "expression": expr,
            "predictions": preds.tolist(),
            "details": {
                "model": "ripple",
                "w": w_best,
                "mse": ripple_mse,
                "degrees": {"sin": int(ds_opt), "cos": int(ds_opt), "poly": int(dp_opt)},
                "harmonic": (include_harm is not None),
            },
        }