import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = kwargs.get("random_state", 42)
        self.max_terms = kwargs.get("max_terms", 24)
        self.use_validation = kwargs.get("use_validation", True)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        rng = np.random.default_rng(self.random_state)
        n, d = X.shape
        assert d == 4, "X must have 4 columns: x1, x2, x3, x4"

        # Train/validation split
        idx = np.arange(n)
        rng.shuffle(idx)
        if self.use_validation and n >= 40:
            n_train = int(0.8 * n)
        else:
            n_train = n
        train_idx = idx[:n_train]
        val_idx = idx[n_train:] if n_train < n else idx[:0]

        X_train, y_train = X[train_idx], y[train_idx]
        X_val, y_val = X[val_idx], y[val_idx] if val_idx.size > 0 else (np.empty((0, 4)), np.empty((0,)))

        # Prepare grids of configurations
        alpha_grid_single = [-0.5, -0.3, -0.2, -0.1, -0.05, -0.03, -0.02, -0.01]
        alpha_pairs = [(-0.1, -0.02), (-0.2, -0.05), (-0.5, -0.1), (-0.3, -0.03), (-0.2, -0.01)]
        configs = []
        # Base poly only
        configs.append({"base_deg": 3, "exp_deg": 2, "alphas": []})
        # Base deg 2 + single exp
        for a in alpha_grid_single:
            configs.append({"base_deg": 2, "exp_deg": 2, "alphas": [a]})
        # Base deg 3 + single exp (subset)
        for a in [-0.1, -0.05, -0.02]:
            configs.append({"base_deg": 3, "exp_deg": 2, "alphas": [a]})
        # Base deg 2 + pair of exps
        for a, b in alpha_pairs:
            configs.append({"base_deg": 2, "exp_deg": 2, "alphas": [a, b]})

        # Regularization strengths
        lam_list = [0.0, 1e-6, 1e-4]
        # Target number of terms to select
        K_list = [8, 12, 16, 20, min(self.max_terms, 24)]

        # Precompute powers for efficiency
        def monomial_powers(dims, max_degree):
            res = []
            def rec(prefix, idx, remaining):
                if idx == dims - 1:
                    res.append(tuple(prefix + [remaining]))
                    return
                for e in range(remaining + 1):
                    rec(prefix + [e], idx + 1, remaining - e)
            for total in range(max_degree + 1):
                rec([], 0, total)
            return res

        def eval_monomials(X_local, powers_list, x_pows_cache):
            # x_pows_cache: list of [np.ndarray for exponent 0..max_deg] per variable
            n_local = X_local.shape[0]
            out = np.empty((n_local, len(powers_list)), dtype=float)
            for j, pw in enumerate(powers_list):
                v = np.ones(n_local, dtype=float)
                # Multiply across variables
                if pw[0] != 0:
                    v = v * x_pows_cache[0][pw[0]]
                if pw[1] != 0:
                    v = v * x_pows_cache[1][pw[1]]
                if pw[2] != 0:
                    v = v * x_pows_cache[2][pw[2]]
                if pw[3] != 0:
                    v = v * x_pows_cache[3][pw[3]]
                out[:, j] = v
            return out

        def build_design(X_local, base_deg, exp_deg, alphas):
            # Prepare caches of powers up to max degree encountered
            max_pow = max(base_deg, exp_deg, 2)  # need 2 for r2
            x_pows_cache = []
            for i in range(4):
                xi = X_local[:, i]
                cache_i = [np.ones_like(xi)]
                for e in range(1, max_pow + 1):
                    cache_i.append(cache_i[-1] * xi)
                x_pows_cache.append(cache_i)

            # r2 = sum of squares
            r2 = x_pows_cache[0][2]
            for i in range(1, 4):
                r2 = r2 + x_pows_cache[i][2]

            col_infos = []
            blocks = []
            # Base polynomial
            base_pows = monomial_powers(4, base_deg)
            A_base = eval_monomials(X_local, base_pows, x_pows_cache)
            blocks.append(A_base)
            for pw in base_pows:
                col_infos.append(("base", None, pw))

            # Exponential-polynomial terms
            if alphas:
                exp_pows = monomial_powers(4, exp_deg)
                for a in alphas:
                    E = np.exp(a * r2)
                    A_exp_poly = eval_monomials(X_local, exp_pows, x_pows_cache) * E[:, None]
                    blocks.append(A_exp_poly)
                    for pw in exp_pows:
                        col_infos.append(("exp", a, pw))

            A = np.concatenate(blocks, axis=1)
            return A, col_infos

        def find_intercept_index(col_infos):
            for j, (grp, a, pw) in enumerate(col_infos):
                if grp == "base" and pw == (0, 0, 0, 0):
                    return j
            return None

        def std_per_column(A_local):
            s = A_local.std(axis=0)
            s[s == 0.0] = 1.0
            return s

        def fit_ridge(A_local, y_local, lam):
            if lam <= 0:
                c, *_ = np.linalg.lstsq(A_local, y_local, rcond=None)
                return c
            AtA = A_local.T @ A_local
            m = AtA.shape[0]
            AtA = AtA + lam * np.eye(m)
            Aty = A_local.T @ y_local
            try:
                c = np.linalg.solve(AtA, Aty)
            except np.linalg.LinAlgError:
                c, *_ = np.linalg.lstsq(A_local, y_local, rcond=None)
            return c

        def evaluate_mse(pred, target):
            if target.size == 0:
                return 0.0
            diff = target - pred
            return float(np.mean(diff * diff))

        def select_top_k_indices(coefs, stds, intercept_idx, K):
            m = coefs.shape[0]
            eff = np.abs(coefs) * stds
            idx_all = np.arange(m)
            if intercept_idx is not None:
                mask = np.ones(m, dtype=bool)
                mask[intercept_idx] = False
                idx_sorted = idx_all[mask][np.argsort(-eff[mask])]
                top = idx_sorted[:max(0, K)]
                sel = np.concatenate(([intercept_idx], top))
            else:
                idx_sorted = idx_all[np.argsort(-eff)]
                sel = idx_sorted[:max(1, K)]
            return np.unique(sel)

        # Search best configuration
        best = {
            "score": np.inf,
            "config": None,
            "sel_idx": None,
            "coefs": None,
            "col_infos": None
        }

        for cfg in configs:
            base_deg, exp_deg, alphas = cfg["base_deg"], cfg["exp_deg"], cfg["alphas"]

            A_tr, col_infos = build_design(X_train, base_deg, exp_deg, alphas)
            A_val, _ = build_design(X_val, base_deg, exp_deg, alphas)
            intercept_idx = find_intercept_index(col_infos)
            stds = std_per_column(A_tr)

            for lam in lam_list:
                coefs_ridge = fit_ridge(A_tr, y_train, lam)

                for K in K_list:
                    sel_idx = select_top_k_indices(coefs_ridge, stds, intercept_idx, K)
                    # Refit on selected features (OLS)
                    c_sub, *_ = np.linalg.lstsq(A_tr[:, sel_idx], y_train, rcond=None)
                    if A_val.shape[0] > 0:
                        pred_val = A_val[:, sel_idx] @ c_sub
                        mse_val = evaluate_mse(pred_val, y_val)
                    else:
                        # No validation set; use training MSE
                        pred_val = A_tr[:, sel_idx] @ c_sub
                        mse_val = evaluate_mse(pred_val, y_train)

                    # Slight complexity penalty to encourage simpler models
                    complexity_penalty = 1e-8 * len(sel_idx)
                    score = mse_val + complexity_penalty

                    if score < best["score"]:
                        best.update({
                            "score": score,
                            "config": (base_deg, exp_deg, tuple(alphas)),
                            "sel_idx": sel_idx.copy(),
                            "coefs": c_sub.copy(),
                            "col_infos": [col_infos[i] for i in sel_idx]
                        })

        # Final refit on full data using best config/indices
        if best["config"] is None:
            # Fallback: simple linear regression baseline
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
            A_lin = np.column_stack([x1, x2, x3, x4, np.ones_like(x1)])
            coeffs, *_ = np.linalg.lstsq(A_lin, y, rcond=None)
            a, b, c, d, e = coeffs
            expression = f"({a:.12g})*x1 + ({b:.12g})*x2 + ({c:.12g})*x3 + ({d:.12g})*x4 + ({e:.12g})"
            preds = A_lin @ coeffs
            return {
                "expression": expression,
                "predictions": preds.tolist(),
                "details": {}
            }

        base_deg, exp_deg, alphas_tuple = best["config"]
        alphas = list(alphas_tuple)
        # Build full design for selected config
        A_full, col_infos_full = build_design(X, base_deg, exp_deg, alphas)
        # Map selected indices from best selection to full columns
        # best["col_infos"] holds the info tuples for selected indices; we need to find their positions in the full matrix
        info_to_indices = {}
        for j, info in enumerate(col_infos_full):
            info_to_indices.setdefault(info, []).append(j)

        sel_indices_full = []
        for info in best["col_infos"]:
            # Pick the first matching column index
            sel_indices_full.append(info_to_indices[info][0])

        sel_indices_full = np.array(sel_indices_full, dtype=int)
        # Refit on all data with selected features
        coefs_full, *_ = np.linalg.lstsq(A_full[:, sel_indices_full], y, rcond=None)

        # Build expression string with factorization by exponential groups
        # Group selected terms
        selected_infos = [col_infos_full[i] for i in sel_indices_full]
        # Map from group to list of (power, coef)
        groups = {}  # key: ("base", None) or ("exp", alpha) -> list of (power, coef)
        for coef, info in zip(coefs_full, selected_infos):
            grp, a, pw = info
            key = (grp, a)
            groups.setdefault(key, []).append((pw, coef))

        def fmt_coef(c):
            return f"{c:.12g}"

        def monomial_str(pw):
            # pw: tuple of 4 ints
            parts = []
            exps = [("x1", pw[0]), ("x2", pw[1]), ("x3", pw[2]), ("x4", pw[3])]
            for name, e in exps:
                if e == 0:
                    continue
                elif e == 1:
                    parts.append(name)
                else:
                    parts.append(f"{name}**{e}")
            if not parts:
                return "1"
            return " * ".join(parts)

        def polynomial_str(term_list):
            # term_list: list of (power, coef)
            # Create sum of c*monomial; if monomial == "1", just c
            # Filter out exact zeros
            pieces = []
            for pw, coef in term_list:
                if coef == 0.0:
                    continue
                mono = monomial_str(pw)
                if mono == "1":
                    pieces.append(f"({fmt_coef(coef)})")
                else:
                    pieces.append(f"({fmt_coef(coef)})*({mono})")
            if not pieces:
                return "0"
            return " + ".join(pieces)

        r2_str = "(x1**2 + x2**2 + x3**2 + x4**2)"
        expr_parts = []

        # Base group first
        base_key = ("base", None)
        if base_key in groups:
            poly_s = polynomial_str(groups[base_key])
            if poly_s != "0":
                expr_parts.append(f"({poly_s})")

        # Exponential groups in sorted order of alpha
        exp_keys = sorted([k for k in groups.keys() if k[0] == "exp"], key=lambda k: float(k[1]))
        for key in exp_keys:
            a = key[1]
            poly_s = polynomial_str(groups[key])
            if poly_s == "0":
                continue
            expr_parts.append(f"exp(({fmt_coef(a)})*{r2_str})*({poly_s})")

        if not expr_parts:
            # Fallback to constant zero
            expression = "0"
            preds = np.zeros_like(y)
        else:
            expression = " + ".join(expr_parts)
            preds = A_full[:, sel_indices_full] @ coefs_full

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }