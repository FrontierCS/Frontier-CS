import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = kwargs.get("random_state", 42)

    def _ridge(self, A, b, lam=1e-12):
        n_features = A.shape[1]
        AtA = A.T @ A
        # Add ridge to diagonal
        AtA.flat[:: n_features + 1] += lam
        try:
            coef = np.linalg.solve(AtA, A.T @ b)
        except np.linalg.LinAlgError:
            coef, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        return coef

    def _mse(self, y_true, y_pred):
        diff = y_true - y_pred
        return float(np.mean(diff * diff))

    def _build_features(self, r, r2, c, variant):
        # variant: "r" or "r2"
        if variant == "r":
            arg = c * r
        else:
            arg = c * r2
        s = np.sin(arg)
        cc = np.cos(arg)
        ones = np.ones_like(r)
        Phi = np.column_stack([
            ones,          # 0
            r,             # 1
            r2,            # 2
            s,             # 3
            r * s,         # 4
            r2 * s,        # 5
            cc,            # 6
            r * cc,        # 7
            r2 * cc,       # 8
        ])
        return Phi

    def _select_c_grid(self, r, r2):
        # Dynamic grids based on data range
        r_max = float(np.max(r)) if r.size > 0 else 1.0
        r2_max = float(np.max(r2)) if r2.size > 0 else 1.0
        r_max = max(r_max, 1e-6)
        r2_max = max(r2_max, 1e-6)

        # Number of oscillations across domain [0, r_max] or [0, r2_max]
        # Use a reasonable range of oscillations
        k_r = np.arange(2, 61)  # 2..60 oscillations
        c_grid_r = (2.0 * np.pi * k_r) / r_max

        k_r2 = np.arange(1, 31)  # 1..30 oscillations over r2
        c_grid_r2 = (2.0 * np.pi * k_r2) / r2_max

        # Add a couple of extra candidates
        extras_r = np.array([c_grid_r[0] * 0.5, c_grid_r[-1] * 1.25])
        extras_r2 = np.array([c_grid_r2[0] * 0.5, c_grid_r2[-1] * 1.25])

        c_grid_r = np.unique(np.clip(np.concatenate([c_grid_r, extras_r]), 1e-6, np.inf))
        c_grid_r2 = np.unique(np.clip(np.concatenate([c_grid_r2, extras_r2]), 1e-6, np.inf))

        return c_grid_r, c_grid_r2

    def _refine_c(self, r, r2, c_best, variant, Xtr, ytr, Xva, yva):
        # Local refinement around best c: multiplicative window
        # generate relative multipliers around 1.0
        rel = np.linspace(0.9, 1.1, 21)
        best_c = c_best
        best_mse = np.inf
        for m in rel:
            c = max(1e-9, c_best * float(m))
            Phi_tr = self._build_features(r[Xtr], r2[Xtr], c, variant)
            beta = self._ridge(Phi_tr, ytr)
            Phi_va = self._build_features(r[Xva], r2[Xva], c, variant)
            mse = self._mse(yva, Phi_va @ beta)
            if mse < best_mse:
                best_mse = mse
                best_c = c
        return best_c

    def _fit_for_variant(self, r, r2, c_grid, variant, idx_tr, idx_va, y):
        best = {
            "mse": np.inf,
            "c": None,
            "beta": None,
        }
        Xtr = idx_tr
        Xva = idx_va
        ytr = y[Xtr]
        yva = y[Xva]

        # Precompute for speed? Build on the fly; cost is small.
        for c in c_grid:
            Phi_tr = self._build_features(r[Xtr], r2[Xtr], c, variant)
            beta = self._ridge(Phi_tr, ytr, lam=1e-10)
            Phi_va = self._build_features(r[Xva], r2[Xva], c, variant)
            mse = self._mse(yva, Phi_va @ beta)
            if mse < best["mse"]:
                best["mse"] = mse
                best["c"] = float(c)
                best["beta"] = beta

        # Refine c locally around the best candidate
        c_refined = self._refine_c(r, r2, best["c"], variant, Xtr, ytr, Xva, yva)
        Phi_tr = self._build_features(r[Xtr], r2[Xtr], c_refined, variant)
        beta = self._ridge(Phi_tr, ytr, lam=1e-12)
        Phi_va = self._build_features(r[Xva], r2[Xva], c_refined, variant)
        mse = self._mse(yva, Phi_va @ beta)

        if mse < best["mse"]:
            best["mse"] = mse
            best["c"] = float(c_refined)
            best["beta"] = beta

        return best

    def _feature_scores(self, Phi, beta):
        # Return score for each feature as |beta| * sqrt(mean(phi^2))
        # This estimates contribution magnitude
        meansq = np.mean(Phi * Phi, axis=0)
        scale = np.sqrt(meansq + 1e-18)
        return np.abs(beta) * scale

    def _select_features(self, r, r2, c, variant, idx_tr, idx_va, y):
        # Build full feature set
        Phi_tr_full = self._build_features(r[idx_tr], r2[idx_tr], c, variant)
        Phi_va_full = self._build_features(r[idx_va], r2[idx_va], c, variant)

        ytr = y[idx_tr]
        yva = y[idx_va]

        beta_full = self._ridge(Phi_tr_full, ytr, lam=1e-12)
        scores = self._feature_scores(Phi_tr_full, beta_full)

        # Indices:
        base = [0, 1, 2]  # 1, r, r2
        trig = [3, 4, 5, 6, 7, 8]  # sin and cos terms and multiplied

        # Rank trig features by score
        trig_sorted = [trig[i] for i in np.argsort(scores[trig])[::-1]]

        best = {
            "mse": np.inf,
            "idx": None,
            "beta": None,
        }

        # Try K from 2..6 trig features
        for K in range(2, 7):
            chosen_trig = trig_sorted[:K]
            # Try combinations of base terms: include intercept (0) always; try with/without r and r2
            base_options = [
                [0],
                [0, 1],
                [0, 2],
                [0, 1, 2],
            ]
            for b in base_options:
                idx = b + chosen_trig
                Phi_tr = Phi_tr_full[:, idx]
                Phi_va = Phi_va_full[:, idx]
                beta = self._ridge(Phi_tr, ytr, lam=1e-12)
                mse = self._mse(yva, Phi_va @ beta)
                if mse < best["mse"]:
                    best["mse"] = mse
                    best["idx"] = idx
                    best["beta"] = beta

        # Final small pruning based on tiny coefficients (relative to y scale)
        idx = best["idx"]
        beta = best["beta"]
        Phi_tr = Phi_tr_full[:, idx]
        # compute contribution scales
        ystd = float(np.std(ytr)) + 1e-12
        meansq_sel = np.mean(Phi_tr * Phi_tr, axis=0)
        scale_sel = np.sqrt(meansq_sel + 1e-18)
        contrib = np.abs(beta) * scale_sel / ystd
        keep_mask = contrib > 1e-3  # threshold
        if not np.any(keep_mask):
            # Ensure at least intercept is kept
            keep_mask[0] = True
        idx_pruned = [idx[i] for i in range(len(idx)) if keep_mask[i]]
        Phi_tr2 = Phi_tr_full[:, idx_pruned]
        beta2 = self._ridge(Phi_tr2, ytr, lam=1e-12)
        Phi_va2 = Phi_va_full[:, idx_pruned]
        mse2 = self._mse(yva, Phi_va2 @ beta2)

        if mse2 <= best["mse"]:
            best["mse"] = mse2
            best["idx"] = idx_pruned
            best["beta"] = beta2

        return best

    def _expression_from_model(self, idx, beta, c, variant):
        # Build expression string from selected features and coefficients
        # Feature mapping reference (by index):
        # 0: 1
        # 1: r = ((x1**2 + x2**2)**0.5)
        # 2: r2 = (x1**2 + x2**2)
        # 3: sin(arg)
        # 4: r*sin(arg)
        # 5: r2*sin(arg)
        # 6: cos(arg)
        # 7: r*cos(arg)
        # 8: r2*cos(arg)
        r2_str = "(x1**2 + x2**2)"
        r_str = f"({r2_str}**0.5)"
        if variant == "r":
            arg_str = f"({format(c, '.12g')}*{r_str})"
        else:
            arg_str = f"({format(c, '.12g')}*{r2_str})"

        def term_str(j, coef):
            cstr = format(float(coef), ".12g")
            if j == 0:
                return f"({cstr})"
            elif j == 1:
                return f"({cstr}*{r_str})"
            elif j == 2:
                return f"({cstr}*{r2_str})"
            elif j == 3:
                return f"({cstr}*sin{arg_str})" if arg_str.startswith("(") else f"({cstr}*sin({arg_str}))"
            elif j == 4:
                inner = f"{r_str}*sin{arg_str}" if arg_str.startswith("(") else f"{r_str}*sin({arg_str})"
                return f"({cstr}*{inner})"
            elif j == 5:
                inner = f"{r2_str}*sin{arg_str}" if arg_str.startswith("(") else f"{r2_str}*sin({arg_str})"
                return f"({cstr}*{inner})"
            elif j == 6:
                return f"({cstr}*cos{arg_str})" if arg_str.startswith("(") else f"({cstr}*cos({arg_str}))"
            elif j == 7:
                inner = f"{r_str}*cos{arg_str}" if arg_str.startswith("(") else f"{r_str}*cos({arg_str})"
                return f"({cstr}*{inner})"
            elif j == 8:
                inner = f"{r2_str}*cos{arg_str}" if arg_str.startswith("(") else f"{r2_str}*cos({arg_str})"
                return f"({cstr}*{inner})"
            else:
                return "(0)"

        terms = [term_str(j, coef) for j, coef in zip(idx, beta)]
        if not terms:
            return "0"
        expr = " + ".join(terms)
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        n = X.shape[0]
        x1 = X[:, 0].astype(float)
        x2 = X[:, 1].astype(float)
        r2 = x1 * x1 + x2 * x2
        r = np.sqrt(np.maximum(r2, 0.0))

        # Train/validation split
        rng = np.random.default_rng(self.random_state)
        idx = np.arange(n)
        rng.shuffle(idx)
        split = int(max(1, np.floor(0.8 * n)))
        idx_tr = np.sort(idx[:split])
        idx_va = np.sort(idx[split:]) if split < n else idx_tr  # if very small data, use same

        # Prepare c grids
        c_grid_r, c_grid_r2 = self._select_c_grid(r, r2)

        # Fit for both variants
        best_r = self._fit_for_variant(r, r2, c_grid_r, "r", idx_tr, idx_va, y)
        best_r2 = self._fit_for_variant(r, r2, c_grid_r2, "r2", idx_tr, idx_va, y)

        # Choose best variant
        if best_r["mse"] <= best_r2["mse"]:
            variant = "r"
            c_best = best_r["c"]
        else:
            variant = "r2"
            c_best = best_r2["c"]

        # Feature selection with chosen variant
        best_sel = self._select_features(r, r2, c_best, variant, idx_tr, idx_va, y)
        idx_final = best_sel["idx"]
        beta_final = best_sel["beta"]

        # Fit on full dataset with selected features
        Phi_full = self._build_features(r, r2, c_best, variant)
        Phi_sel = Phi_full[:, idx_final]
        beta_full = self._ridge(Phi_sel, y, lam=1e-12)
        y_pred = Phi_sel @ beta_full

        # Build expression
        expression = self._expression_from_model(idx_final, beta_full, c_best, variant)

        return {
            "expression": expression,
            "predictions": y_pred.tolist(),
            "details": {
                "variant": variant,
                "frequency": float(c_best),
                "num_terms": int(len(idx_final)),
            }
        }
