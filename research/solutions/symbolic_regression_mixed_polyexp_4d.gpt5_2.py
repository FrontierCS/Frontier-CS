import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.deg = int(kwargs.get("deg", 3))
        self.max_terms = int(kwargs.get("max_terms", 25))
        self.alpha_grid_size = int(kwargs.get("alpha_grid_size", 30))
        self.top_k_alphas = int(kwargs.get("top_k_alphas", 6))
        self.rcond = float(kwargs.get("rcond", 1e-9))
        self.coeff_threshold_rel = float(kwargs.get("coeff_threshold_rel", 1e-4))

    def _build_monomials(self, X, deg):
        n = X.shape[0]
        # Precompute powers up to deg for each variable
        powX = []
        for j in range(4):
            pj = [np.ones(n)]
            if deg >= 1:
                pj.append(X[:, j].copy())
                for p in range(2, deg + 1):
                    pj.append(pj[-1] * X[:, j])
            powX.append(pj)

        # Generate exponent tuples for monomials with total degree <= deg
        exps = []
        for s in range(deg + 1):
            for e1 in range(s + 1):
                rem1 = s - e1
                for e2 in range(rem1 + 1):
                    rem2 = rem1 - e2
                    for e3 in range(rem2 + 1):
                        e4 = rem2 - e3
                        exps.append((e1, e2, e3, e4))

        # Build numeric features and corresponding strings
        feats = []
        terms_str = []
        for e in exps:
            f = powX[0][e[0]] * powX[1][e[1]] * powX[2][e[2]] * powX[3][e[3]]
            feats.append(f)
            parts = []
            if e[0] == 1:
                parts.append("x1")
            elif e[0] > 1:
                parts.append(f"x1**{e[0]}")
            if e[1] == 1:
                parts.append("x2")
            elif e[1] > 1:
                parts.append(f"x2**{e[1]}")
            if e[2] == 1:
                parts.append("x3")
            elif e[2] > 1:
                parts.append(f"x3**{e[2]}")
            if e[3] == 1:
                parts.append("x4")
            elif e[3] > 1:
                parts.append(f"x4**{e[3]}")
            if len(parts) == 0:
                terms_str.append("1")
            else:
                terms_str.append("*".join(parts))

        B = np.column_stack(feats)
        return B, terms_str

    def _lstsq(self, A, y):
        try:
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=self.rcond)
        except Exception:
            # Fallback to pseudo-inverse
            coef = np.linalg.pinv(A) @ y
        return coef

    def _fit_with_alphas(self, B, y, r2, alphas):
        # Alphas is a list (possibly empty)
        n, m = B.shape
        blocks = [B]
        g_cache = {}
        for a in alphas:
            if a not in g_cache:
                g_cache[a] = np.exp(-a * r2)
            g = g_cache[a]
            blocks.append(B * g[:, None])
        A = np.hstack(blocks)
        coef = self._lstsq(A, y)
        pred = A @ coef
        mse = float(np.mean((y - pred) ** 2))
        return mse, coef, A

    def _select_alphas(self, B, y, r2, alpha_candidates):
        # Baseline (no gaussian)
        best_mse0, best_coef0, best_A0 = self._fit_with_alphas(B, y, r2, [])
        best_single = (best_mse0, [], best_coef0, best_A0)

        # Single alpha search
        single_results = []
        for a in alpha_candidates:
            if a <= 0:
                continue
            mse, coef, A = self._fit_with_alphas(B, y, r2, [a])
            single_results.append((mse, [a], coef, A))
        if single_results:
            single_results.sort(key=lambda t: t[0])
            best_single = single_results[0]

        # Two alphas search over top-k single candidates
        best_double = (best_single[0], best_single[1], best_single[2], best_single[3])
        top_k = min(self.top_k_alphas, len(single_results))
        if top_k >= 1:
            top_alphas = [single_results[i][1][0] for i in range(top_k)]
            seen_pairs = set()
            for i in range(top_k):
                for j in range(i, top_k):
                    a1, a2 = top_alphas[i], top_alphas[j]
                    pair_key = (min(a1, a2), max(a1, a2))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    mse, coef, A = self._fit_with_alphas(B, y, r2, [a1, a2])
                    if mse < best_double[0]:
                        best_double = (mse, [a1, a2], coef, A)

        # Choose best among baseline, single, double
        candidates = [
            (best_mse0, [], best_coef0, best_A0),
            best_single,
            best_double,
        ]
        candidates.sort(key=lambda t: t[0])
        return candidates[0]

    def _build_expression(self, kept_blocks, kept_idx_in_block, kept_coefs, base_terms_str, alphas):
        # kept_blocks: list of block indices (0=base, 1=first gaussian, 2=second gaussian)
        # kept_idx_in_block: list of indices within base terms (0..M-1)
        # kept_coefs: list of coefficients
        # alphas: list of gaussian alphas (length K)
        # Construct g strings
        r2_str = "(x1**2 + x2**2 + x3**2 + x4**2)"
        g_strs = []
        for a in alphas:
            g_strs.append(f"exp(-({float(a):.12g})*{r2_str})")

        terms = []
        for blk, j, c in zip(kept_blocks, kept_idx_in_block, kept_coefs):
            c_val = float(c)
            if abs(c_val) < 1e-15:
                continue
            base_str = base_terms_str[j]
            if blk == 0:
                # base polynomial term
                if base_str == "1":
                    term_str = f"{c_val:.12g}"
                else:
                    term_str = f"({c_val:.12g})*({base_str})"
            else:
                g_idx = blk - 1
                g_str = g_strs[g_idx]
                if base_str == "1":
                    term_str = f"({c_val:.12g})*{g_str}"
                else:
                    term_str = f"({c_val:.12g})*(({base_str})*{g_str})"
            terms.append(term_str)

        if not terms:
            # Fallback to zero
            return "0"
        expression = " + ".join(terms)
        return expression

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, d = X.shape
        if d != 4:
            # Fallback: simple linear if dimensions mismatch
            A_lin = np.column_stack([X, np.ones(n)])
            coef, _, _, _ = np.linalg.lstsq(A_lin, y, rcond=None)
            a, b, c, dcoef, e = coef
            expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}*x3 + {dcoef:.6f}*x4 + {e:.6f}"
            preds = A_lin @ coef
            return {
                "expression": expression,
                "predictions": preds.tolist(),
                "details": {}
            }

        # Build polynomial basis up to degree 3
        try:
            B, base_terms_str = self._build_monomials(X, self.deg)
        except Exception:
            # Fallback to degree 2 if memory or other issues
            B, base_terms_str = self._build_monomials(X, 2)

        # Compute r2
        r2 = np.sum(X * X, axis=1)

        # Alpha candidates (avoid degenerate median)
        med_r2 = float(np.median(r2))
        if med_r2 <= 1e-12:
            med_r2 = 1.0
        # Log-spaced around a wide range scaled by median r2
        try:
            alphas_nonzero = (10.0 ** np.linspace(-3, 3, self.alpha_grid_size)) / med_r2
        except Exception:
            alphas_nonzero = (10.0 ** np.linspace(-3, 3, 30)) / med_r2

        # Select alphas and fit
        mse_best, chosen_alphas, coef_best, A_best = self._select_alphas(B, y, r2, list(alphas_nonzero))

        # Prune coefficients to reduce complexity
        w = coef_best.copy()
        abs_w = np.abs(w)
        if abs_w.size == 0:
            # Fallback to constant mean
            c0 = float(np.mean(y))
            expression = f"{c0:.12g}"
            preds = np.full_like(y, c0)
            return {"expression": expression, "predictions": preds.tolist(), "details": {}}

        # Determine block structure
        M = B.shape[1]
        n_blocks = 1 + len(chosen_alphas)  # base + gaussians
        # Map linear index to (block, idx_in_block)
        blocks_for_cols = []
        idx_in_block = []
        for blk in range(n_blocks):
            for j in range(M):
                blocks_for_cols.append(blk)
                idx_in_block.append(j)
        blocks_for_cols = np.array(blocks_for_cols)
        idx_in_block = np.array(idx_in_block)

        # Thresholding
        thr = float(np.max(abs_w)) * self.coeff_threshold_rel
        keep_mask = abs_w >= thr
        keep_idx = np.where(keep_mask)[0]
        if keep_idx.size == 0:
            keep_idx = np.array([int(np.argmax(abs_w))])

        # Limit to max_terms
        if keep_idx.size > self.max_terms:
            order = np.argsort(-abs_w)[:self.max_terms]
            keep_idx = np.sort(order)

        # Refit with reduced feature set
        A_reduced = A_best[:, keep_idx]
        w_reduced = self._lstsq(A_reduced, y)
        preds = A_reduced @ w_reduced

        kept_blocks = blocks_for_cols[keep_idx].tolist()
        kept_idx_in_block = idx_in_block[keep_idx].tolist()
        kept_coefs = w_reduced.tolist()

        expression = self._build_expression(kept_blocks, kept_idx_in_block, kept_coefs, base_terms_str, chosen_alphas)

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }
