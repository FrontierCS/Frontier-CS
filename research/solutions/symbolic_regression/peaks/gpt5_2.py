import numpy as np

class Solution:
    def __init__(self, max_terms=5, alpha_values=None, random_state=42):
        self.max_terms = max_terms
        if alpha_values is None:
            self.alpha_values = [1e-8, 1e-6, 1e-4, 1e-3, 1e-2]
        else:
            self.alpha_values = alpha_values
        self.random_state = random_state

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Model A: Forward-selected peaks-inspired basis
        features_a = self._build_peaks_features(X)
        expr_a, preds_a, mse_a = self._fit_forward_selection(features_a, y)

        # Model B: Classic peaks formula (fixed coefficients from MATLAB peaks)
        expr_b, preds_b, mse_b = self._classic_peaks_fixed(X, y)

        # Model C: Compact RBF basis (data-driven centers)
        expr_c, preds_c, mse_c = self._fit_rbf_model(X, y, k=5)

        # Pick best by MSE; if close, prefer simpler expression by term count
        candidates = [
            ("A", expr_a, preds_a, mse_a, self._expr_term_count(expr_a)),
            ("B", expr_b, preds_b, mse_b, self._expr_term_count(expr_b)),
            ("C", expr_c, preds_c, mse_c, self._expr_term_count(expr_c)),
        ]

        # Choose minimal MSE; tie-breaker: fewer terms
        best = min(candidates, key=lambda t: (t[3], t[4]))
        expression = best[1]
        predictions = best[2]

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }

    def _fmt(self, c):
        if np.isfinite(c):
            if abs(c) < 1e-14:
                return "0"
            s = format(float(c), ".12g")
            if s == "-0":
                s = "0"
            return s
        return "0"

    def _mse(self, y_true, y_pred):
        diff = y_true - y_pred
        return float(np.mean(diff * diff))

    def _solve_ridge(self, A, y, alpha):
        # Ridge regression with unpenalized intercept (first column)
        p = A.shape[1]
        if p == 0:
            return np.zeros(0)
        # Compute normal equations
        ATA = A.T @ A
        ATy = A.T @ y
        # Regularize
        reg = np.eye(p) * alpha
        reg[0, 0] = 0.0  # do not penalize intercept
        try:
            w = np.linalg.solve(ATA + reg, ATy)
        except np.linalg.LinAlgError:
            # Fallback to pseudo-inverse
            w = np.linalg.pinv(ATA + reg) @ ATy
        return w

    def _best_alpha(self, A, y):
        best_alpha = self.alpha_values[0]
        best_mse = np.inf
        for a in self.alpha_values:
            w = self._solve_ridge(A, y, a)
            pred = A @ w
            mse = self._mse(y, pred)
            if mse < best_mse:
                best_mse = mse
                best_alpha = a
        return best_alpha

    def _build_peaks_features(self, X):
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Helper strings
        e0_str = "exp(-(x1**2) - (x2**2))"
        e1_str = "exp(-(x1**2) - (x2 + 1)**2)"
        e2_str = "exp(-((x1 + 1)**2) - (x2**2))"

        e0 = np.exp(-(x1**2) - (x2**2))
        e1 = np.exp(-(x1**2) - (x2 + 1.0)**2)
        e2 = np.exp(-((x1 + 1.0)**2) - (x2**2))

        features = []

        # Classic Peaks components
        f1 = (1.0 - x1)**2 * e1
        features.append((f1, "(1 - x1)**2*{}".format(e1_str)))

        f2 = (x1/5.0 - x1**3 - x2**5) * e0
        features.append((f2, "(x1/5 - x1**3 - x2**5)*{}".format(e0_str)))

        f3 = e2
        features.append((f3, e2_str))

        # Additional localized polynomial-exponential terms for flexibility
        f4 = x1 * e0
        features.append((f4, "x1*{}".format(e0_str)))

        f5 = x2 * e0
        features.append((f5, "x2*{}".format(e0_str)))

        f6 = (x1**2) * e0
        features.append((f6, "(x1**2)*{}".format(e0_str)))

        f7 = (x2**2) * e0
        features.append((f7, "(x2**2)*{}".format(e0_str)))

        f8 = (1.0 - x2)**2 * np.exp(-(x2**2) - (x1 + 1.0)**2)
        features.append((f8, "(1 - x2)**2*exp(-(x2**2) - (x1 + 1)**2)"))

        return features

    def _fit_forward_selection(self, features, y):
        # Forward selection over provided features with ridge regression
        n = y.shape[0]
        ones = np.ones(n)
        selected = []
        selected_exprs = []
        selected_arrays = []
        best_models = []  # list of tuples (coefs, exprs, mse, preds)

        # Start with intercept-only model
        A = ones.reshape(-1, 1)
        alpha = self._best_alpha(A, y)
        w = self._solve_ridge(A, y, alpha)
        pred = A @ w
        mse = self._mse(y, pred)
        best_models.append((w, [], mse, pred))

        max_terms = max(1, self.max_terms)
        remaining_idx = list(range(len(features)))

        for step in range(max_terms):
            best_local = None
            best_local_idx = None
            for idx in remaining_idx:
                arr, expr = features[idx]
                A_cand = np.column_stack([ones] + selected_arrays + [arr])
                # Choose best alpha for this candidate quickly (use two alphas)
                # but here we use predefined grid for robustness
                best_alpha = self._best_alpha(A_cand, y)
                w_cand = self._solve_ridge(A_cand, y, best_alpha)
                pred_cand = A_cand @ w_cand
                mse_cand = self._mse(y, pred_cand)
                if (best_local is None) or (mse_cand < best_local[2]):
                    best_local = (w_cand, selected_exprs + [expr], mse_cand, pred_cand, best_alpha)
                    best_local_idx = idx
            if best_local is None:
                break
            # Accept the best feature of this step
            w_cand, exprs_cand, mse_cand, pred_cand, alpha_cand = best_local
            best_models.append((w_cand, exprs_cand, mse_cand, pred_cand))
            # Update selected
            arr_sel, expr_sel = features[best_local_idx]
            selected_arrays.append(arr_sel)
            selected_exprs.append(expr_sel)
            remaining_idx.remove(best_local_idx)

        # Choose best among models found
        best = min(best_models, key=lambda t: t[2])
        w_best, exprs_best, mse_best, pred_best = best

        # Build expression string
        expression = self._build_expression_from_coefs(w_best, exprs_best)

        return expression, pred_best, mse_best

    def _build_expression_from_coefs(self, w, exprs):
        # w: array of shape (1 + k,), where w[0] is intercept
        # exprs: list of strings of length k
        terms = []
        c0 = w[0] if len(w) > 0 else 0.0
        if abs(c0) > 1e-12 or len(w) == 1:
            terms.append(self._fmt(c0))
        for coef, expr in zip(w[1:], exprs):
            if abs(coef) <= 1e-12:
                continue
            coef_str = self._fmt(coef)
            terms.append("({})*({})".format(coef_str, expr))
        if len(terms) == 0:
            return "0"
        return " + ".join(terms)

    def _classic_peaks_fixed(self, X, y):
        x1 = X[:, 0]
        x2 = X[:, 1]
        g1 = (1.0 - x1)**2 * np.exp(-(x1**2) - (x2 + 1.0)**2)
        g2 = (x1/5.0 - x1**3 - x2**5) * np.exp(-(x1**2) - (x2**2))
        g3 = np.exp(-((x1 + 1.0)**2) - (x2**2))
        preds = 3.0 * g1 - 10.0 * g2 - (1.0/3.0) * g3
        mse = self._mse(y, preds)
        expr = "3*(1 - x1)**2*exp(-(x1**2) - (x2 + 1)**2) - 10*(x1/5 - x1**3 - x2**5)*exp(-(x1**2) - (x2**2)) - 1/3*exp(-((x1 + 1)**2) - (x2**2))"
        return expr, preds, mse

    def _fit_rbf_model(self, X, y, k=5):
        # Data-driven compact RBF model: y ≈ c0 + Σ wi * exp(-gamma * ((x1-ci1)^2 + (x2-ci2)^2))
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Choose centers using quantiles for robustness
        q_low1, q_med1, q_high1 = np.quantile(x1, [0.2, 0.5, 0.8])
        q_low2, q_med2, q_high2 = np.quantile(x2, [0.2, 0.5, 0.8])

        centers = [
            (q_low1, q_low2),
            (q_low1, q_high2),
            (q_high1, q_low2),
            (q_high1, q_high2),
            (q_med1, q_med2),
        ]

        # Adjust k if fewer or more centers desired
        if k < len(centers):
            rng = np.random.default_rng(self.random_state)
            idxs = rng.choice(len(centers), size=k, replace=False)
            centers = [centers[i] for i in idxs]
        elif k > len(centers):
            # Add additional centers by jittering medians slightly
            rng = np.random.default_rng(self.random_state)
            while len(centers) < k:
                jitter1 = float(rng.normal(scale=0.1)) * (np.std(x1) + 1e-9)
                jitter2 = float(rng.normal(scale=0.1)) * (np.std(x2) + 1e-9)
                centers.append((q_med1 + jitter1, q_med2 + jitter2))

        # Width parameter gamma based on data spread
        r1 = np.std(x1) + 1e-9
        r2 = np.std(x2) + 1e-9
        sigma = 0.8 * (r1 + r2) / 2.0 + 1e-9
        gamma = 1.0 / (2.0 * sigma * sigma)

        Phi = [np.ones(n)]
        exprs = []
        for (c1, c2) in centers:
            arr = np.exp(-gamma * ((x1 - c1)**2 + (x2 - c2)**2))
            Phi.append(arr)
            exprs.append("exp(-(" + self._fmt(gamma) + ")*((x1 - (" + self._fmt(c1) + "))**2 + (x2 - (" + self._fmt(c2) + "))**2))")

        A = np.column_stack(Phi)
        # Mild ridge to avoid degeneracy
        alpha = self._best_alpha(A, y)
        w = self._solve_ridge(A, y, alpha)
        preds = A @ w

        # Prune tiny coefficients (except intercept) to reduce complexity, and refit if needed
        mask = [True]  # keep intercept
        pruned_exprs = []
        for coef, expr in zip(w[1:], exprs):
            keep = abs(coef) > 1e-8
            mask.append(keep)
            if keep:
                pruned_exprs.append(expr)
        if sum(mask) < len(mask):
            A_pruned = A[:, mask]
            alpha2 = self._best_alpha(A_pruned, y)
            w2 = self._solve_ridge(A_pruned, y, alpha2)
            preds = A_pruned @ w2
            # Build expression
            expression = self._build_expression_from_coefs(w2, pruned_exprs)
            mse = self._mse(y, preds)
            return expression, preds, mse
        else:
            expression = self._build_expression_from_coefs(w, exprs)
            mse = self._mse(y, preds)
            return expression, preds, mse

    def _expr_term_count(self, expr):
        # Rough measure of terms: count top-level '+' as separators
        # This is only used for tie-breaking; not used in scoring
        if not isinstance(expr, str) or len(expr.strip()) == 0:
            return 0
        # Count '+' that are not in scientific notation (e±)
        count = 1
        i = 0
        while i < len(expr):
            if expr[i] == '+':
                # Check for scientific notation indicator 'e+'
                if not (i > 0 and expr[i-1] in 'eE'):
                    count += 1
            i += 1
        return count