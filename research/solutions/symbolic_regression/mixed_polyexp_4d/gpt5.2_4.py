import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 0))
        self.max_omp_terms = int(kwargs.get("max_omp_terms", 8))
        self.subsample = int(kwargs.get("subsample", 5000))

    @staticmethod
    def _safe_exp_arg(arg):
        return np.clip(arg, -50.0, 50.0)

    @staticmethod
    def _ridge_solve(A, b, lam=1e-10):
        k = A.shape[1]
        ATA = A.T @ A
        ATA.flat[::k + 1] += lam
        ATb = A.T @ b
        try:
            return np.linalg.solve(ATA, ATb)
        except np.linalg.LinAlgError:
            return np.linalg.lstsq(A, b, rcond=None)[0]

    @staticmethod
    def _omp(Phi, y, k, Phi_normed=None, tol=1e-12):
        n, m = Phi.shape
        if Phi_normed is None:
            norms = np.linalg.norm(Phi, axis=0)
            norms = np.where(norms > 0, norms, 1.0)
            Phi_normed = Phi / norms

        selected = []
        residual = y.astype(np.float64, copy=True)

        last_rss = float(np.dot(residual, residual))
        for _ in range(min(k, m)):
            corr = np.abs(Phi_normed.T @ residual)
            if selected:
                corr[selected] = 0.0
            j = int(np.argmax(corr))
            if not np.isfinite(corr[j]) or corr[j] < tol:
                break
            selected.append(j)

            A = Phi[:, selected]
            beta = Solution._ridge_solve(A, y, lam=1e-10)
            residual = y - A @ beta
            rss = float(np.dot(residual, residual))
            if last_rss - rss <= tol * max(1.0, last_rss):
                break
            last_rss = rss

        if not selected:
            return [], np.zeros((0,), dtype=np.float64)

        A = Phi[:, selected]
        beta = Solution._ridge_solve(A, y, lam=1e-10)
        return selected, beta

    @staticmethod
    def _build_poly_terms(X):
        x1 = X[:, 0].astype(np.float64, copy=False)
        x2 = X[:, 1].astype(np.float64, copy=False)
        x3 = X[:, 2].astype(np.float64, copy=False)
        x4 = X[:, 3].astype(np.float64, copy=False)

        x1_2 = x1 * x1
        x2_2 = x2 * x2
        x3_2 = x3 * x3
        x4_2 = x4 * x4

        x1_3 = x1_2 * x1
        x2_3 = x2_2 * x2
        x3_3 = x3_2 * x3
        x4_3 = x4_2 * x4

        x1x2 = x1 * x2
        x1x3 = x1 * x3
        x1x4 = x1 * x4
        x2x3 = x2 * x3
        x2x4 = x2 * x4
        x3x4 = x3 * x4

        terms = []
        exprs = []

        def add(col, expr):
            terms.append(col)
            exprs.append(expr)

        ones = np.ones_like(x1)
        add(ones, "1")

        add(x1, "x1")
        add(x2, "x2")
        add(x3, "x3")
        add(x4, "x4")

        add(x1_2, "x1**2")
        add(x2_2, "x2**2")
        add(x3_2, "x3**2")
        add(x4_2, "x4**2")

        add(x1x2, "x1*x2")
        add(x1x3, "x1*x3")
        add(x1x4, "x1*x4")
        add(x2x3, "x2*x3")
        add(x2x4, "x2*x4")
        add(x3x4, "x3*x4")

        add(x1_3, "x1**3")
        add(x2_3, "x2**3")
        add(x3_3, "x3**3")
        add(x4_3, "x4**3")

        add(x1_2 * x2, "x1**2*x2")
        add(x1_2 * x3, "x1**2*x3")
        add(x1_2 * x4, "x1**2*x4")

        add(x2_2 * x1, "x2**2*x1")
        add(x2_2 * x3, "x2**2*x3")
        add(x2_2 * x4, "x2**2*x4")

        add(x3_2 * x1, "x3**2*x1")
        add(x3_2 * x2, "x3**2*x2")
        add(x3_2 * x4, "x3**2*x4")

        add(x4_2 * x1, "x4**2*x1")
        add(x4_2 * x2, "x4**2*x2")
        add(x4_2 * x3, "x4**2*x3")

        add(x1x2 * x3, "x1*x2*x3")
        add(x1x2 * x4, "x1*x2*x4")
        add(x1x3 * x4, "x1*x3*x4")
        add(x2x3 * x4, "x2*x3*x4")

        Phi = np.column_stack(terms).astype(np.float64, copy=False)
        return Phi, exprs

    @staticmethod
    def _format_float(a):
        if not np.isfinite(a):
            return "0.0"
        if a == 0.0:
            return "0.0"
        s = format(float(a), ".12g")
        if "e" in s or "E" in s:
            s = s.replace("E", "e")
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _build_linear_combo_expr(terms, coeffs, coef_threshold=0.0):
        parts = []
        for term, c in zip(terms, coeffs):
            if not np.isfinite(c):
                continue
            if abs(c) <= coef_threshold:
                continue
            sign = "-" if c < 0 else "+"
            ac = abs(c)
            if term == "1":
                piece = Solution._format_float(ac)
            else:
                cstr = Solution._format_float(ac)
                if cstr == "1":
                    piece = term
                else:
                    piece = cstr + "*" + term
            parts.append((sign, piece))

        if not parts:
            return "0.0"

        sign0, piece0 = parts[0]
        expr = piece0 if sign0 == "+" else "-" + piece0
        for sgn, piece in parts[1:]:
            expr += " " + sgn + " " + piece
        return expr

    @staticmethod
    def _mse(y, yhat):
        r = y - yhat
        return float(np.mean(r * r))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).astype(np.float64, copy=False)
        n = X.shape[0]

        x1 = X[:, 0].astype(np.float64, copy=False)
        x2 = X[:, 1].astype(np.float64, copy=False)
        x3 = X[:, 2].astype(np.float64, copy=False)
        x4 = X[:, 3].astype(np.float64, copy=False)

        # Baseline linear regression MSE
        A_lin = np.column_stack([x1, x2, x3, x4, np.ones_like(x1)]).astype(np.float64, copy=False)
        beta_lin = self._ridge_solve(A_lin, y, lam=1e-10)
        yhat_lin = A_lin @ beta_lin
        mse_base = self._mse(y, yhat_lin)

        # Polynomial library
        Phi, term_exprs = self._build_poly_terms(X)
        norms = np.linalg.norm(Phi, axis=0)
        norms = np.where(norms > 0, norms, 1.0)
        Phi_normed = Phi / norms

        # Subsample for candidate selection
        rng = np.random.default_rng(self.random_state)
        if n > self.subsample:
            idx = rng.choice(n, size=self.subsample, replace=False)
            idx.sort()
        else:
            idx = None

        if idx is None:
            Phi_s = Phi
            Phi_normed_s = Phi_normed
            y_s = y
            x1_s, x2_s, x3_s, x4_s = x1, x2, x3, x4
        else:
            Phi_s = Phi[idx]
            Phi_normed_s = Phi_normed[idx]
            y_s = y[idx]
            x1_s, x2_s, x3_s, x4_s = x1[idx], x2[idx], x3[idx], x4[idx]

        # Precompute quadratic forms (subset + full)
        def quad_parts(a1, a2, a3, a4):
            q12 = a1 * a1 + a2 * a2
            q34 = a3 * a3 + a4 * a4
            r2 = q12 + q34
            cross = a1 * a2 + a3 * a4
            return q12, q34, r2, cross

        q12_s, q34_s, r2_s, cross_s = quad_parts(x1_s, x2_s, x3_s, x4_s)
        q12_f, q34_f, r2_f, cross_f = quad_parts(x1, x2, x3, x4)

        # Candidate search: multiplicative model y = exp(arg)*poly
        theta_grid = np.array([-2.0, -1.5, -1.0, -0.75, -0.5, -0.25, -0.125], dtype=np.float64)
        theta_grid2 = np.array([-2.0, -1.0, -0.5, -0.25, -0.125], dtype=np.float64)
        theta_cross = np.array([-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0], dtype=np.float64)

        best = {
            "mse_s": np.inf,
            "kind": "none",
            "params": None,
            "sel": None,
            "beta": None,
        }

        def eval_candidate_on_subset(arg_s, kind, params):
            arg_s = self._safe_exp_arg(arg_s)
            w_s = np.exp(arg_s)
            t_s = y_s / w_s
            sel, beta = self._omp(Phi_s, t_s, k=self.max_omp_terms, Phi_normed=Phi_normed_s)
            if not sel:
                return
            yhat_s = w_s * (Phi_s[:, sel] @ beta)
            mse_s = self._mse(y_s, yhat_s)
            if mse_s < best["mse_s"]:
                best["mse_s"] = mse_s
                best["kind"] = kind
                best["params"] = params
                best["sel"] = sel
                best["beta"] = beta

        # No exp (arg = 0)
        eval_candidate_on_subset(np.zeros_like(y_s), kind="noexp", params=None)

        # exp(theta * r2)
        for th in theta_grid:
            eval_candidate_on_subset(th * r2_s, kind="r2", params=(float(th),))

        # exp(thetaA*q12 + thetaB*q34)
        for thA in theta_grid2:
            for thB in theta_grid2:
                eval_candidate_on_subset(thA * q12_s + thB * q34_s, kind="split", params=(float(thA), float(thB)))

        # exp(theta1*r2 + theta2*cross)
        for th1 in np.array([-2.0, -1.0, -0.5, -0.25], dtype=np.float64):
            for th2 in theta_cross:
                eval_candidate_on_subset(th1 * r2_s + th2 * cross_s, kind="r2cross", params=(float(th1), float(th2)))

        # Refit on full data with best candidate (still multiplicative)
        def arg_full_from_best():
            kind = best["kind"]
            params = best["params"]
            if kind == "noexp":
                return np.zeros_like(y, dtype=np.float64), "1"
            if kind == "r2":
                (th,) = params
                arg = th * r2_f
                s = f"exp({self._format_float(th)}*(x1**2+x2**2+x3**2+x4**2))"
                return arg, s
            if kind == "split":
                thA, thB = params
                if abs(thA - thB) <= 1e-14:
                    th = thA
                    arg = th * r2_f
                    s = f"exp({self._format_float(th)}*(x1**2+x2**2+x3**2+x4**2))"
                    return arg, s
                arg = thA * q12_f + thB * q34_f
                a = self._format_float(thA)
                b = self._format_float(thB)
                s = f"exp({a}*(x1**2+x2**2)+{b}*(x3**2+x4**2))"
                return arg, s
            if kind == "r2cross":
                th1, th2 = params
                arg = th1 * r2_f + th2 * cross_f
                a = self._format_float(th1)
                b = self._format_float(th2)
                if b == "0.0":
                    s = f"exp({a}*(x1**2+x2**2+x3**2+x4**2))"
                else:
                    s = f"exp({a}*(x1**2+x2**2+x3**2+x4**2)+{b}*(x1*x2+x3*x4))"
                return arg, s
            return np.zeros_like(y, dtype=np.float64), "1"

        arg_f, wexpr = arg_full_from_best()
        arg_f = self._safe_exp_arg(arg_f)
        w_f = np.exp(arg_f)
        t_f = y / w_f

        sel_f, beta_f = self._omp(Phi, t_f, k=self.max_omp_terms, Phi_normed=Phi_normed)
        if sel_f:
            A = Phi[:, sel_f]
            beta_f = self._ridge_solve(A, t_f, lam=1e-10)
            poly_terms = [term_exprs[j] for j in sel_f]
            poly_expr = self._build_linear_combo_expr(poly_terms, beta_f, coef_threshold=0.0)

            if wexpr == "1":
                expression = poly_expr
                predictions = (Phi[:, sel_f] @ beta_f)
            else:
                expression = f"({poly_expr})*{wexpr}"
                predictions = w_f * (Phi[:, sel_f] @ beta_f)
            mse_mult = self._mse(y, predictions)
        else:
            expression = self._build_linear_combo_expr(["x1", "x2", "x3", "x4", "1"], beta_lin, coef_threshold=0.0)
            predictions = yhat_lin
            mse_mult = mse_base

        # Stage2 (optional): if multiplicative fit not good, fit sparse linear combo of poly*exp(...) features
        # This increases robustness but may raise complexity. Only activate if needed.
        activate_stage2 = False
        if np.isfinite(mse_base) and mse_base > 0:
            if not np.isfinite(mse_mult) or mse_mult > 0.30 * mse_base:
                activate_stage2 = True
        else:
            if not np.isfinite(mse_mult):
                activate_stage2 = True

        if activate_stage2:
            # Build weight set
            w_specs = [("1", np.zeros_like(y_s), np.zeros_like(y))]
            for th in np.array([-2.0, -1.0, -0.5, -0.25], dtype=np.float64):
                w_specs.append((f"exp({self._format_float(th)}*(x1**2+x2**2+x3**2+x4**2))", th * r2_s, th * r2_f))
            for th in np.array([-2.0, -1.0, -0.5, -0.25], dtype=np.float64):
                w_specs.append((f"exp({self._format_float(th)}*(x1**2+x2**2))", th * q12_s, th * q12_f))
            for th in np.array([-2.0, -1.0, -0.5, -0.25], dtype=np.float64):
                w_specs.append((f"exp({self._format_float(th)}*(x3**2+x4**2))", th * q34_s, th * q34_f))

            # Precompute weights (subset)
            W_s = []
            W_f = []
            W_expr = []
            for s_expr, arg_s2, arg_f2 in w_specs:
                arg_s2 = self._safe_exp_arg(arg_s2)
                arg_f2 = self._safe_exp_arg(arg_f2)
                W_s.append(np.exp(arg_s2))
                W_f.append(np.exp(arg_f2))
                W_expr.append(s_expr)

            J = len(W_s)
            T = Phi_s.shape[1]

            Phi_sq_s = Phi_s * Phi_s
            norm_jk = np.empty((J, T), dtype=np.float64)
            for j in range(J):
                w2 = W_s[j] * W_s[j]
                norm_jk[j, :] = np.sqrt(Phi_sq_s.T @ w2)
            norm_jk = np.where(norm_jk > 0, norm_jk, 1.0)

            selected_pairs = []
            selected_mask = np.zeros(J * T, dtype=bool)
            residual = y_s.astype(np.float64, copy=True)
            k_total = min(10, J * T)

            for _ in range(k_total):
                best_val = -1.0
                best_pair = None
                for j in range(J):
                    tmp = W_s[j] * residual
                    corr = np.abs(Phi_s.T @ tmp) / norm_jk[j]
                    if selected_pairs:
                        # Mask already selected entries for this j
                        # (fast path: check individually)
                        pass
                    k_idx = int(np.argmax(corr))
                    val = float(corr[k_idx])
                    flat = j * T + k_idx
                    if selected_mask[flat]:
                        # find next best by partial scan
                        order = np.argsort(-corr)
                        found = False
                        for k2 in order[:10]:
                            flat2 = j * T + int(k2)
                            if not selected_mask[flat2]:
                                k_idx = int(k2)
                                val = float(corr[k_idx])
                                flat = flat2
                                found = True
                                break
                        if not found:
                            continue
                    if np.isfinite(val) and val > best_val:
                        best_val = val
                        best_pair = (j, k_idx)

                if best_pair is None or best_val <= 1e-12:
                    break

                j, k_idx = best_pair
                selected_pairs.append((j, k_idx))
                selected_mask[j * T + k_idx] = True

                cols = [W_s[jj] * Phi_s[:, kk] for (jj, kk) in selected_pairs]
                A = np.column_stack(cols)
                coef = self._ridge_solve(A, y_s, lam=1e-10)
                residual = y_s - A @ coef

                if not np.isfinite(residual).all():
                    break

            if selected_pairs:
                cols_f = [W_f[jj] * Phi[:, kk] for (jj, kk) in selected_pairs]
                A_f = np.column_stack(cols_f)
                coef_f = self._ridge_solve(A_f, y, lam=1e-10)
                yhat_f = A_f @ coef_f
                mse_stage2 = self._mse(y, yhat_f)

                if np.isfinite(mse_stage2) and mse_stage2 < mse_mult:
                    # Build expression
                    feature_exprs = []
                    for (jj, kk) in selected_pairs:
                        w_e = W_expr[jj]
                        t_e = term_exprs[kk]
                        if w_e == "1":
                            f_e = t_e
                        else:
                            if t_e == "1":
                                f_e = w_e
                            else:
                                f_e = f"({t_e})*{w_e}"
                        feature_exprs.append(f_e)
                    expression = self._build_linear_combo_expr(feature_exprs, coef_f, coef_threshold=0.0)
                    predictions = yhat_f
                    mse_mult = mse_stage2

        if predictions is None or (not np.isfinite(predictions).all()):
            predictions = yhat_lin
            expression = self._build_linear_combo_expr(["x1", "x2", "x3", "x4", "1"], beta_lin, coef_threshold=0.0)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }