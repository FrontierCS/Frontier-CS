import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 42))
        self.max_centers = int(kwargs.get("max_centers", 9))
        self.ridge_lambda = float(kwargs.get("ridge_lambda", 1e-6))
        self._rng = np.random.default_rng(self.random_state)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, d = X.shape
        if d != 2:
            raise ValueError("X must have shape (n, 2)")

        x1 = X[:, 0]
        x2 = X[:, 1]

        candidates = []

        # Candidate 1: Peaks-like basis only (3 features) + intercept
        cand1 = self._fit_with_features(
            X, y,
            feature_builders=self._peaks_features_basic,
            prune_strength=1e-4
        )
        candidates.append(cand1)

        # Candidate 2: Peaks-like basis + quadratic polynomial + intercept
        cand2 = self._fit_with_features(
            X, y,
            feature_builders=self._peaks_features_poly2,
            prune_strength=5e-5
        )
        candidates.append(cand2)

        # Candidate 3: RBFs from k-means + quadratic polynomial + intercept
        cand3 = self._fit_with_features(
            X, y,
            feature_builders=self._rbf_poly_features,
            prune_strength=5e-4
        )
        candidates.append(cand3)

        # Select best candidate based on MSE, with tie-break on #terms (simplicity)
        best = candidates[0]
        for c in candidates[1:]:
            if c["mse"] < best["mse"] * 0.99:  # at least 1% better MSE
                best = c
            elif abs(c["mse"] - best["mse"]) <= 0.01 * best["mse"]:
                # Prefer simpler if MSE similar
                if c["num_terms"] < best["num_terms"]:
                    best = c

        return {
            "expression": best["expression"],
            "predictions": best["predictions"].tolist(),
            "details": {}
        }

    def _format_float(self, v: float) -> str:
        if abs(v) < 1e-15:
            return "0"
        s = f"{float(v):.12g}"
        # Ensure there's a decimal or exponent for integers to be explicit float
        if "e" not in s and "." not in s:
            s += ".0"
        return s

    def _ridge(self, A: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
        m = A.shape[1]
        AtA = A.T @ A
        try:
            w = np.linalg.solve(AtA + lam * np.eye(m), A.T @ y)
        except np.linalg.LinAlgError:
            w, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        return w

    def _build_expression(self, coefs: np.ndarray, feat_strs: list) -> str:
        # coefs aligned with feat_strs; feat_strs elements are valid expressions or "1" for intercept
        terms = []
        for c, s in zip(coefs, feat_strs):
            if abs(c) < 1e-15:
                continue
            coef_abs = abs(c)
            coef_str = self._format_float(coef_abs)
            if s == "1":
                t = coef_str
            else:
                # Always include coefficient explicitly
                t = f"{coef_str}*({s})"
            sign = "-" if c < 0 else "+"
            terms.append((sign, t))

        if not terms:
            return "0.0"

        # Construct expression starting with first term (carry its sign)
        first_sign, first_term = terms[0]
        expr = ("" if first_sign == "+" else "-") + first_term
        for sign, t in terms[1:]:
            expr += f" {sign} {t}"
        return expr

    def _prune_by_contribution(self, A: np.ndarray, w: np.ndarray, y: np.ndarray, feat_strs: list, prune_strength: float):
        # Prune features whose contribution RMS < threshold = prune_strength * y_scale
        y_scale = max(np.std(y), 1e-8)
        contrib_rms = np.sqrt(np.mean((A * w.reshape(1, -1))**2, axis=0))
        threshold = prune_strength * y_scale
        keep = contrib_rms >= threshold

        # Ensure at least one term kept
        if not np.any(keep):
            # Keep the single largest contributor
            idx = int(np.argmax(contrib_rms))
            keep[idx] = True

        A_pruned = A[:, keep]
        w_pruned = w[keep]
        feat_strs_pruned = [s for s, k in zip(feat_strs, keep) if k]
        return A_pruned, w_pruned, feat_strs_pruned

    def _fit_with_features(self, X: np.ndarray, y: np.ndarray, feature_builders, prune_strength: float):
        # feature_builders: function returning (A_without_intercept, feat_strs_without_intercept), we add intercept internally
        A_no_int, feat_strs_no_int = feature_builders(X, y)
        n = X.shape[0]
        ones = np.ones((n, 1), dtype=float)
        A = np.column_stack([ones, A_no_int])
        feat_strs = ["1"] + feat_strs_no_int

        w = self._ridge(A, y, self.ridge_lambda)

        # Prune small contributions (including intercept considered as a feature)
        A_pruned, w_pruned, feat_strs_pruned = self._prune_by_contribution(A, w, y, feat_strs, prune_strength)
        y_pred = A_pruned @ w_pruned
        mse = float(np.mean((y - y_pred) ** 2))

        expression = self._build_expression(w_pruned, feat_strs_pruned)
        return {
            "expression": expression,
            "predictions": y_pred,
            "mse": mse,
            "num_terms": len(w_pruned)
        }

    # Feature builders

    def _peaks_features_basic(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]
        # Peaks-like basis
        g1 = ((1.0 - x1)**2) * np.exp(-(x1**2) - (x2 + 1.0)**2)
        g2 = (x1/5.0 - x1**3 - x2**5) * np.exp(-(x1**2) - (x2**2))
        g3 = np.exp(-(x1 + 1.0)**2 - (x2**2))

        A = np.column_stack([g1, g2, g3])
        s1 = "((1 - x1)**2)*exp(-(x1**2) - (x2 + 1)**2)"
        s2 = "(x1/5 - x1**3 - x2**5)*exp(-(x1**2) - (x2**2))"
        s3 = "exp(-(x1 + 1)**2 - x2**2)"
        feat_strs = [s1, s2, s3]
        return A, feat_strs

    def _peaks_features_poly2(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]
        # Peaks-like basis
        g1 = ((1.0 - x1)**2) * np.exp(-(x1**2) - (x2 + 1.0)**2)
        g2 = (x1/5.0 - x1**3 - x2**5) * np.exp(-(x1**2) - (x2**2))
        g3 = np.exp(-(x1 + 1.0)**2 - (x2**2))
        # Quadratic polynomial terms
        p1 = x1
        p2 = x2
        p3 = x1**2
        p4 = x1 * x2
        p5 = x2**2

        A = np.column_stack([g1, g2, g3, p1, p2, p3, p4, p5])
        feat_strs = [
            "((1 - x1)**2)*exp(-(x1**2) - (x2 + 1)**2)",
            "(x1/5 - x1**3 - x2**5)*exp(-(x1**2) - (x2**2))",
            "exp(-(x1 + 1)**2 - x2**2)",
            "x1",
            "x2",
            "x1**2",
            "x1*x2",
            "x2**2",
        ]
        return A, feat_strs

    def _kmeans_plus_plus(self, X: np.ndarray, K: int, seed: int):
        n = X.shape[0]
        rng = np.random.default_rng(seed)
        centers = np.empty((K, 2), dtype=float)
        # pick first center randomly
        idx = int(rng.integers(0, n))
        centers[0] = X[idx]
        # distances squared to the nearest center
        d2 = np.sum((X - centers[0])**2, axis=1)
        for i in range(1, K):
            total = float(np.sum(d2))
            if total <= 1e-18:
                idx = int(rng.integers(0, n))
            else:
                probs = d2 / total
                r = float(rng.random())
                csum = np.cumsum(probs)
                idx = int(np.searchsorted(csum, r))
            centers[i] = X[idx]
            new_d2 = np.sum((X - centers[i])**2, axis=1)
            d2 = np.minimum(d2, new_d2)
        return centers

    def _kmeans(self, X: np.ndarray, K: int, n_init: int = 2, max_iter: int = 50):
        best_inertia = np.inf
        best_centers = None
        best_labels = None
        seeds = self._rng.integers(1_000_000_000, size=n_init)
        for s in seeds:
            centers = self._kmeans_plus_plus(X, K, int(s))
            for _ in range(max_iter):
                # Assign
                dists = self._pairwise_sq_dists(X, centers)
                labels = np.argmin(dists, axis=1)
                # Update
                new_centers = np.empty_like(centers)
                for k in range(K):
                    mask = labels == k
                    if np.any(mask):
                        new_centers[k] = X[mask].mean(axis=0)
                    else:
                        # Reinitialize to a random point
                        new_centers[k] = X[int(self._rng.integers(0, X.shape[0]))]
                shift = np.max(np.linalg.norm(new_centers - centers, axis=1))
                centers = new_centers
                if shift < 1e-7:
                    break
            inertia = float(np.sum((X - centers[labels])**2))
            if inertia < best_inertia:
                best_inertia = inertia
                best_centers = centers
                best_labels = labels
        return best_centers, best_labels

    def _pairwise_sq_dists(self, X: np.ndarray, C: np.ndarray):
        # X: (n,2), C:(K,2) -> (n,K)
        # Compute (x - c)^2 sum using broadcasting (small K ensures memory is fine)
        return np.sum((X[:, None, :] - C[None, :, :])**2, axis=2)

    def _rbf_params_from_kmeans(self, X: np.ndarray, K: int):
        K = max(2, min(K, X.shape[0]))
        centers, labels = self._kmeans(X, K, n_init=2, max_iter=50)
        # Per-cluster variances
        global_var = np.var(X, axis=0) + 1e-12
        floor_var = 0.05 * global_var + 1e-12
        variances = np.empty((K, 2), dtype=float)
        for k in range(K):
            mask = labels == k
            if np.sum(mask) >= 2:
                var_k = np.var(X[mask], axis=0)
                var_k = np.maximum(var_k, floor_var)
                variances[k] = var_k
            elif np.sum(mask) == 1:
                variances[k] = np.maximum(global_var, floor_var)
            else:
                variances[k] = np.maximum(global_var, floor_var)
        return centers, variances

    def _rbf_poly_features(self, X: np.ndarray, y: np.ndarray):
        n = X.shape[0]
        # choose K based on n
        if n < 30:
            K = min(4, n)
        else:
            K = int(max(5, min(self.max_centers, np.sqrt(n) // 2 + 5)))
        centers, variances = self._rbf_params_from_kmeans(X, K)
        x1 = X[:, 0]
        x2 = X[:, 1]

        # RBF features
        rbf_feats = []
        rbf_strs = []
        for (cx, cy), (v1, v2) in zip(centers, variances):
            s1 = 2.0 * float(v1) + 1e-12
            s2 = 2.0 * float(v2) + 1e-12
            e = -(((x1 - cx)**2) / s1 + ((x2 - cy)**2) / s2)
            phi = np.exp(e)
            rbf_feats.append(phi)
            cx_s = self._format_float(cx)
            cy_s = self._format_float(cy)
            s1_s = self._format_float(s1)
            s2_s = self._format_float(s2)
            rbf_strs.append(f"exp(-(((x1 - {cx_s})**2)/{s1_s} + ((x2 - {cy_s})**2)/{s2_s}))")

        # Quadratic polynomial terms
        p1 = x1
        p2 = x2
        p3 = x1**2
        p4 = x1 * x2
        p5 = x2**2

        A = np.column_stack(rbf_feats + [p1, p2, p3, p4, p5])
        feat_strs = rbf_strs + ["x1", "x2", "x1**2", "x1*x2", "x2**2"]
        return A, feat_strs
