import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.max_terms = int(kwargs.get("max_terms", 22))
        self.random_state = int(kwargs.get("random_state", 42))

    def _fmt(self, x):
        return format(float(x), ".16g")

    def _ridge(self, A, y, alpha):
        m = A.shape[1]
        G = A.T @ A
        G.flat[::m + 1] += alpha
        try:
            w = np.linalg.solve(G, A.T @ y)
        except np.linalg.LinAlgError:
            w = np.linalg.lstsq(G, A.T @ y, rcond=None)[0]
        return w

    def _standardize(self, Fraw, has_constant=True):
        F = Fraw.astype(np.float64, copy=True)
        n, m = F.shape
        mu = np.zeros(m, dtype=np.float64)
        sigma = np.ones(m, dtype=np.float64)
        start = 1 if has_constant else 0
        if start < m:
            mu[start:] = F[:, start:].mean(axis=0)
            sigma[start:] = F[:, start:].std(axis=0)
            sigma[sigma < 1e-12] = 1.0
            F[:, start:] = (F[:, start:] - mu[start:]) / sigma[start:]
        return F, mu, sigma

    def _convert_to_original(self, w, mu, sigma, has_constant=True):
        m = w.shape[0]
        start = 1 if has_constant else 0
        coef = np.zeros(m, dtype=np.float64)
        coef[start:] = w[start:] / sigma[start:]
        intercept = (w[0] if has_constant else 0.0) - float(np.sum(w[start:] * (mu[start:] / sigma[start:])))
        return intercept, coef

    def _choose_alpha(self, F, y, rng, alphas):
        n = F.shape[0]
        idx = rng.permutation(n)
        split = int(0.8 * n)
        tr = idx[:split]
        va = idx[split:]
        A_tr = F[tr]
        y_tr = y[tr]
        A_va = F[va]
        y_va = y[va]
        best_alpha = alphas[0]
        best_mse = np.inf
        for a in alphas:
            w = self._ridge(A_tr, y_tr, a)
            pred = A_va @ w
            mse = float(np.mean((pred - y_va) ** 2))
            if mse < best_mse:
                best_mse = mse
                best_alpha = a
        return best_alpha

    def _build_features(self, x1, x2):
        n = x1.shape[0]
        features = []

        def add(expr, val):
            if np.any(~np.isfinite(val)):
                return
            features.append((expr, val))

        # Precompute basics
        r2_val = x1 * x1 + x2 * x2
        r_val = np.sqrt(r2_val)
        ones = np.ones_like(x1)

        r_str = "((x1**2 + x2**2)**0.5)"
        r2_str = "((x1**2 + x2**2))"

        # Base polynomial features
        add("x1", x1)
        add("x2", x2)
        add("x1**2", x1**2)
        add("x2**2", x2**2)
        add("(x1*x2)", x1 * x2)
        add(r_str, r_val)
        add(r2_str, r2_val)
        add("log(1.0 + " + r_str + ")", np.log1p(r_val))

        # Amplitudes
        amp_list = []
        # 1/(1 + c*r2)
        for c in [0.2, 0.5, 1.0]:
            expr = "1.0/(1.0 + " + self._fmt(c) + "*" + r2_str + ")"
            val = 1.0 / (1.0 + c * r_val * r_val)
            amp_list.append((expr, val))
            add(expr, val)
        # 1/(1 + c*r)
        for c in [0.5, 1.0]:
            expr = "1.0/(1.0 + " + self._fmt(c) + "*" + r_str + ")"
            val = 1.0 / (1.0 + c * r_val)
            amp_list.append((expr, val))
            add(expr, val)
        # (1 + r)^-2 and (1 + r2)^-2
        expr = "1.0/(1.0 + " + r_str + ")**2"
        val = 1.0 / (1.0 + r_val) ** 2
        amp_list.append((expr, val))
        add(expr, val)
        expr = "1.0/(1.0 + " + r2_str + ")**2"
        val = 1.0 / (1.0 + r_val * r_val) ** 2
        amp_list.append((expr, val))
        add(expr, val)
        # exp(-a*r2)
        for a in [0.2, 0.5, 1.0]:
            expr = "exp(-" + self._fmt(a) + "*" + r2_str + ")"
            val = np.exp(-a * r_val * r_val)
            amp_list.append((expr, val))
            add(expr, val)

        # Radial trig features with amplitudes
        w_r = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        # include amplitude 1.0 explicitly for carriers
        amp_for_trig = [("1.0", ones)] + amp_list

        for w in w_r:
            carrier_expr_sin = "sin(" + self._fmt(w) + "*" + r_str + ")"
            carrier_expr_cos = "cos(" + self._fmt(w) + "*" + r_str + ")"
            sin_val = np.sin(w * r_val)
            cos_val = np.cos(w * r_val)
            for amp_expr, amp_val in amp_for_trig:
                if amp_expr == "1.0":
                    add(carrier_expr_sin, sin_val)
                    add(carrier_expr_cos, cos_val)
                else:
                    add("(" + amp_expr + ")*" + carrier_expr_sin, amp_val * sin_val)
                    add("(" + amp_expr + ")*" + carrier_expr_cos, amp_val * cos_val)

        # r2 trig features
        w_r2 = [0.5, 1.0, 2.0, 3.0]
        for w in w_r2:
            carrier_expr_sin = "sin(" + self._fmt(w) + "*" + r2_str + ")"
            carrier_expr_cos = "cos(" + self._fmt(w) + "*" + r2_str + ")"
            arg = w * r_val * r_val
            sin_val = np.sin(arg)
            cos_val = np.cos(arg)
            for amp_expr, amp_val in amp_for_trig:
                if amp_expr == "1.0":
                    add(carrier_expr_sin, sin_val)
                    add(carrier_expr_cos, cos_val)
                else:
                    add("(" + amp_expr + ")*" + carrier_expr_sin, amp_val * sin_val)
                    add("(" + amp_expr + ")*" + carrier_expr_cos, amp_val * cos_val)

        # x1/x2 trig with mild amplitude
        amp_xy = [("1.0", ones), ("1.0/(1.0 + " + r2_str + ")", 1.0 / (1.0 + r_val * r_val))]
        k_list = [1.0, 2.0, 3.0, 4.0, 5.0]
        for k in k_list:
            sin1_expr = "sin(" + self._fmt(k) + "*x1)"
            cos1_expr = "cos(" + self._fmt(k) + "*x1)"
            sin2_expr = "sin(" + self._fmt(k) + "*x2)"
            cos2_expr = "cos(" + self._fmt(k) + "*x2)"
            sin1_val = np.sin(k * x1)
            cos1_val = np.cos(k * x1)
            sin2_val = np.sin(k * x2)
            cos2_val = np.cos(k * x2)
            for amp_expr, amp_val in amp_xy:
                if amp_expr == "1.0":
                    add(sin1_expr, sin1_val)
                    add(cos1_expr, cos1_val)
                    add(sin2_expr, sin2_val)
                    add(cos2_expr, cos2_val)
                else:
                    add("(" + amp_expr + ")*" + sin1_expr, amp_val * sin1_val)
                    add("(" + amp_expr + ")*" + cos1_expr, amp_val * cos1_val)
                    add("(" + amp_expr + ")*" + sin2_expr, amp_val * sin2_val)
                    add("(" + amp_expr + ")*" + cos2_expr, amp_val * cos2_val)

        return features

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]

        rng = np.random.default_rng(self.random_state)

        # Build features
        features = self._build_features(x1, x2)

        # Prepare design matrix with intercept
        m = len(features) + 1
        Fraw = np.empty((n, m), dtype=np.float64)
        exprs = ["1.0"]
        Fraw[:, 0] = 1.0
        for j, (expr, val) in enumerate(features, start=1):
            exprs.append(expr)
            Fraw[:, j] = val

        # Standardize
        F, mu, sigma = self._standardize(Fraw, has_constant=True)

        # Alpha selection
        alphas = np.array([1e-8, 3e-8, 1e-7, 3e-7, 1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2], dtype=np.float64)
        alpha = self._choose_alpha(F, y, rng, alphas)

        # Fit on full data
        w = self._ridge(F, y, alpha)
        intercept_full, coef_full = self._convert_to_original(w, mu, sigma, has_constant=True)

        # Select top terms (exclude intercept index 0)
        max_terms = self.max_terms
        if n < 1000:
            max_terms = max(10, self.max_terms - 6)
        elif n > 6000:
            max_terms = self.max_terms + 4

        coef_mag = np.abs(coef_full[1:])
        if coef_mag.size > 0:
            idx_sorted = np.argsort(-coef_mag)
            k = min(max_terms, idx_sorted.size)
            sel_indices = idx_sorted[:k] + 1  # shift due to intercept at 0
        else:
            sel_indices = np.array([], dtype=int)

        # Refit with selected features for sparsity
        mask = np.zeros(m, dtype=bool)
        mask[0] = True
        mask[sel_indices] = True

        Fraw_sub = Fraw[:, mask]
        exprs_sub = [exprs[i] for i in np.where(mask)[0]]

        F_sub, mu_sub, sigma_sub = self._standardize(Fraw_sub, has_constant=True)

        alpha_refit = max(alpha * 0.1, 1e-8)
        w_sub = self._ridge(F_sub, y, alpha_refit)
        intercept_final, coef_final = self._convert_to_original(w_sub, mu_sub, sigma_sub, has_constant=True)

        # Remove tiny coefficients
        nonconst_idx = np.arange(1, coef_final.shape[0])
        keep = np.abs(coef_final[1:]) > (1e-10 * (1.0 + np.std(y)))
        keep_indices = nonconst_idx[keep]
        # Limit to max_terms again (in case refit added more due to numerical)
        if keep_indices.size > max_terms:
            order = np.argsort(-np.abs(coef_final[keep_indices]))
            keep_indices = keep_indices[order[:max_terms]]

        # Build expression string
        terms = []
        if abs(intercept_final) > 1e-12:
            terms.append(self._fmt(intercept_final))
        for idx in keep_indices:
            cj = coef_final[idx]
            ej = exprs_sub[idx]
            if abs(cj) <= 1e-12:
                continue
            terms.append(self._fmt(cj) + "*(" + ej + ")")
        if not terms:
            # Fallback to simple linear model if everything pruned
            a, b, c = np.linalg.lstsq(np.column_stack([x1, x2, np.ones_like(x1)]), y, rcond=None)[0]
            expression = f"{self._fmt(a)}*x1 + {self._fmt(b)}*x2 + {self._fmt(c)}"
            preds = a * x1 + b * x2 + c
            return {"expression": expression, "predictions": preds.tolist(), "details": {}}

        expression = " + ".join(terms)

        # Predictions using final selected model
        y_pred = np.full(n, intercept_final, dtype=np.float64)
        for idx in keep_indices:
            ej_idx = idx
            # Compute corresponding feature values from Fraw_sub (original scale)
            col_values = Fraw_sub[:, ej_idx]
            y_pred += coef_final[ej_idx] * col_values

        return {
            "expression": expression,
            "predictions": y_pred.tolist(),
            "details": {}
        }
