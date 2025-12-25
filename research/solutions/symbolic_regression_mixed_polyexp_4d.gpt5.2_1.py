import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 0))
        self.max_terms = int(kwargs.get("max_terms", 12))
        self.train_frac = float(kwargs.get("train_frac", 0.8))

    @staticmethod
    def _safe_exp(z):
        return np.exp(np.clip(z, -60.0, 60.0))

    @staticmethod
    def _ridge_solve(A, b, ridge=1e-10):
        k = A.shape[1]
        try:
            AtA = A.T @ A
            Atb = A.T @ b
            if ridge > 0:
                reg = np.zeros((k, k), dtype=np.float64)
                reg[1:, 1:] = ridge * np.eye(k - 1, dtype=np.float64)
                AtA = AtA + reg
            return np.linalg.solve(AtA, Atb)
        except Exception:
            return np.linalg.lstsq(A, b, rcond=None)[0]

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        n, d = X.shape
        if d != 4:
            raise ValueError("Expected X with shape (n, 4)")

        x1 = X[:, 0].astype(np.float64, copy=False)
        x2 = X[:, 1].astype(np.float64, copy=False)
        x3 = X[:, 2].astype(np.float64, copy=False)
        x4 = X[:, 3].astype(np.float64, copy=False)

        one = np.ones(n, dtype=np.float64)

        x1_2 = x1 * x1
        x2_2 = x2 * x2
        x3_2 = x3 * x3
        x4_2 = x4 * x4

        x1_3 = x1_2 * x1
        x2_3 = x2_2 * x2
        x3_3 = x3_2 * x3
        x4_3 = x4_2 * x4

        # Polynomial monomials up to degree 3 (selected)
        poly_exprs = []
        poly_vals = []

        poly_exprs.append("1")
        poly_vals.append(one)

        poly_exprs += ["x1", "x2", "x3", "x4"]
        poly_vals += [x1, x2, x3, x4]

        poly_exprs += ["x1**2", "x2**2", "x3**2", "x4**2"]
        poly_vals += [x1_2, x2_2, x3_2, x4_2]

        poly_exprs += ["x1*x2", "x1*x3", "x1*x4", "x2*x3", "x2*x4", "x3*x4"]
        poly_vals += [x1 * x2, x1 * x3, x1 * x4, x2 * x3, x2 * x4, x3 * x4]

        poly_exprs += ["x1**3", "x2**3", "x3**3", "x4**3"]
        poly_vals += [x1_3, x2_3, x3_3, x4_3]

        # xi^2 * xj terms
        vars_expr = ["x1", "x2", "x3", "x4"]
        vars_vals = [x1, x2, x3, x4]
        vars_sq_expr = ["x1**2", "x2**2", "x3**2", "x4**2"]
        vars_sq_vals = [x1_2, x2_2, x3_2, x4_2]
        for i in range(4):
            for j in range(4):
                if i == j:
                    continue
                poly_exprs.append(f"{vars_sq_expr[i]}*{vars_expr[j]}")
                poly_vals.append(vars_sq_vals[i] * vars_vals[j])

        # triple products
        triples = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
        for a, b, c in triples:
            poly_exprs.append(f"{vars_expr[a]}*{vars_expr[b]}*{vars_expr[c]}")
            poly_vals.append(vars_vals[a] * vars_vals[b] * vars_vals[c])

        P = np.column_stack(poly_vals).astype(np.float64, copy=False)
        p = P.shape[1]

        # Damping bases
        sumsq_12 = x1_2 + x2_2
        sumsq_34 = x3_2 + x4_2
        sumsq_123 = x1_2 + x2_2 + x3_2
        sumsq_234 = x2_2 + x3_2 + x4_2
        sumsq_1234 = x1_2 + x2_2 + x3_2 + x4_2
        xsum = x1 + x2 + x3 + x4

        base_terms = [
            ("", None),  # represents 1
            ("x1**2", x1_2),
            ("x2**2", x2_2),
            ("x3**2", x3_2),
            ("x4**2", x4_2),
            ("x1**2 + x2**2", sumsq_12),
            ("x3**2 + x4**2", sumsq_34),
            ("x1**2 + x2**2 + x3**2", sumsq_123),
            ("x2**2 + x3**2 + x4**2", sumsq_234),
            ("x1**2 + x2**2 + x3**2 + x4**2", sumsq_1234),
            ("x1", x1),
            ("x2", x2),
            ("x3", x3),
            ("x4", x4),
            ("x1 + x2 + x3 + x4", xsum),
        ]
        scales = [0.5, 1.0, 2.0]

        damp_exprs = []
        damp_vals = []

        damp_exprs.append("1")
        damp_vals.append(one)

        for base_expr, base_val in base_terms[1:]:
            for s in scales:
                if s == 1.0:
                    expr = f"exp(-({base_expr}))"
                    vals = self._safe_exp(-base_val)
                else:
                    s_str = f"{s:.12g}"
                    expr = f"exp(-{s_str}*({base_expr}))"
                    vals = self._safe_exp(-s * base_val)
                damp_exprs.append(expr)
                damp_vals.append(vals)

        Dm = np.column_stack(damp_vals).astype(np.float64, copy=False)
        dcnt = Dm.shape[1]

        # Build full feature matrix Phi = P * D for all combinations
        m = p * dcnt
        Phi = np.empty((n, m), dtype=np.float32)
        feat_exprs = []
        col = 0
        for j in range(dcnt):
            dj = Dm[:, j].astype(np.float64, copy=False)
            block = (P * dj[:, None]).astype(np.float32, copy=False)
            Phi[:, col:col + p] = block
            damp_e = damp_exprs[j]
            for i in range(p):
                poly_e = poly_exprs[i]
                if poly_e == "1":
                    term_e = damp_e
                elif damp_e == "1":
                    term_e = poly_e
                else:
                    term_e = f"({poly_e})*({damp_e})"
                feat_exprs.append(term_e)
            col += p

        # train/val split
        rng = np.random.default_rng(self.random_state)
        perm = rng.permutation(n)
        ntrain = int(max(10, min(n - 10, round(self.train_frac * n))))
        train_idx = perm[:ntrain]
        val_idx = perm[ntrain:] if ntrain < n else perm[:0]

        y_train = y[train_idx].astype(np.float64, copy=False)
        y_val = y[val_idx].astype(np.float64, copy=False) if val_idx.size > 0 else None

        # Standardize on train for selection and mask out degenerate features
        Phi_train = Phi[train_idx].astype(np.float64, copy=True)  # copy for in-place ops
        mean = Phi_train.mean(axis=0)
        Phi_train -= mean
        norms = np.sqrt(np.sum(Phi_train * Phi_train, axis=0))
        mask = norms > 1e-12

        if not np.any(mask):
            beta0 = float(np.mean(y))
            expression = f"{beta0:.12g}"
            predictions = np.full(n, beta0, dtype=np.float64)
            return {"expression": expression, "predictions": predictions.tolist(), "details": {"complexity": 0}}

        # Reduce feature set
        Phi = Phi[:, mask]
        feat_exprs = [e for e, keep in zip(feat_exprs, mask.tolist()) if keep]
        mean = mean[mask]
        norms = norms[mask]

        # Recompute standardized train matrix Z_train
        Z_train = Phi[train_idx].astype(np.float64, copy=True)
        Z_train -= mean
        Z_train /= norms

        # Baseline: intercept-only
        best_active = []
        best_beta = np.array([np.mean(y_train)], dtype=np.float64)
        best_val_mse = np.inf

        if val_idx.size > 0:
            pred_val0 = np.full(val_idx.size, best_beta[0], dtype=np.float64)
            best_val_mse = float(np.mean((y_val - pred_val0) ** 2))
        else:
            pred_train0 = np.full(train_idx.size, best_beta[0], dtype=np.float64)
            best_val_mse = float(np.mean((y_train - pred_train0) ** 2))

        active = []
        selected = np.zeros(Z_train.shape[1], dtype=bool)

        # residual starts from intercept-only model
        residual = y_train - best_beta[0]

        no_improve_rounds = 0
        for t in range(self.max_terms):
            corr = Z_train.T @ residual
            corr[selected] = 0.0
            j = int(np.argmax(np.abs(corr)))
            if selected[j] or not np.isfinite(corr[j]) or np.abs(corr[j]) < 1e-14:
                break

            active.append(j)
            selected[j] = True

            # Fit on train with intercept + raw features
            Phi_tr_act = Phi[train_idx][:, active].astype(np.float64, copy=False)
            A_tr = np.column_stack([np.ones(train_idx.size, dtype=np.float64), Phi_tr_act])
            beta = self._ridge_solve(A_tr, y_train, ridge=1e-10)

            # Update residual
            pred_tr = A_tr @ beta
            residual = y_train - pred_tr

            # Validate
            if val_idx.size > 0:
                Phi_va_act = Phi[val_idx][:, active].astype(np.float64, copy=False)
                A_va = np.column_stack([np.ones(val_idx.size, dtype=np.float64), Phi_va_act])
                pred_va = A_va @ beta
                val_mse = float(np.mean((y_val - pred_va) ** 2))
            else:
                val_mse = float(np.mean(residual ** 2))

            if val_mse + 1e-12 < best_val_mse:
                best_val_mse = val_mse
                best_active = active.copy()
                best_beta = beta.copy()
                no_improve_rounds = 0
            else:
                no_improve_rounds += 1
                if no_improve_rounds >= 3 and t >= 4:
                    break

        # Refit on full data with best_active
        if len(best_active) > 0:
            Phi_full_act = Phi[:, best_active].astype(np.float64, copy=False)
            A_full = np.column_stack([np.ones(n, dtype=np.float64), Phi_full_act])
            beta_full = self._ridge_solve(A_full, y.astype(np.float64, copy=False), ridge=1e-10)
        else:
            beta_full = np.array([float(np.mean(y))], dtype=np.float64)

        # Build expression
        intercept = float(beta_full[0])
        terms = []
        coefs = []
        if len(best_active) > 0:
            for c, idx in zip(beta_full[1:], best_active):
                if np.isfinite(c) and abs(c) > 1e-12:
                    terms.append(feat_exprs[idx])
                    coefs.append(float(c))

        if abs(intercept) < 1e-12 and not terms:
            expression = "0"
        else:
            expr_parts = [f"{intercept:.12g}"]
            for c, texpr in zip(coefs, terms):
                mag = abs(c)
                if c >= 0:
                    expr_parts.append(f"+ {mag:.12g}*({texpr})")
                else:
                    expr_parts.append(f"- {mag:.12g}*({texpr})")
            expression = " ".join(expr_parts)

        # Predictions
        if len(best_active) > 0:
            Phi_full_act = Phi[:, best_active].astype(np.float64, copy=False)
            predictions = intercept + Phi_full_act @ np.array(coefs, dtype=np.float64)
        else:
            predictions = np.full(n, intercept, dtype=np.float64)

        details = {"complexity": int(len(terms))}
        return {"expression": expression, "predictions": predictions.tolist(), "details": details}