import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 42))
        self.max_terms = int(kwargs.get("max_terms", 20))
        self.max_iter_stridge = int(kwargs.get("max_iter_stridge", 8))

    @staticmethod
    def _format_float(x: float) -> str:
        if not np.isfinite(x):
            return "0.0"
        if abs(x) < 1e-15:
            x = 0.0
        s = "{:.12g}".format(float(x))
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _generate_exponents(nvars: int, max_degree: int):
        exps = []

        def rec(i, remaining, current):
            if i == nvars - 1:
                current.append(remaining)
                exps.append(tuple(current))
                current.pop()
                return
            for e in range(remaining + 1):
                current.append(e)
                rec(i + 1, remaining - e, current)
                current.pop()

        for deg in range(max_degree + 1):
            rec(0, deg, [])
        return exps

    @staticmethod
    def _monomial_str(exp_tuple, var_names):
        parts = []
        for v, e in zip(var_names, exp_tuple):
            if e == 0:
                continue
            if e == 1:
                parts.append(v)
            else:
                parts.append(f"{v}**{e}")
        if not parts:
            return "1"
        return "*".join(parts)

    @staticmethod
    def _build_expr_from_terms(coefs, monom_strs, idxs):
        terms = []
        for j in idxs:
            c = float(coefs[j])
            if not np.isfinite(c) or abs(c) < 1e-15:
                continue
            m = monom_strs[j]
            terms.append((c, m))

        if not terms:
            return "0"

        out = []
        first = True
        for c, m in terms:
            sign = "-" if c < 0 else "+"
            cabs = abs(c)
            cstr = Solution._format_float(cabs)

            if first:
                if c < 0:
                    prefix = "-"
                else:
                    prefix = ""
                first = False
            else:
                prefix = f" {sign} "

            if m == "1":
                out.append(prefix + cstr)
            else:
                out.append(prefix + f"({cstr})*({m})")
        return "".join(out)

    @staticmethod
    def _ridge_solve_from_gram(gram, b, lam):
        p = gram.shape[0]
        lam = float(lam)
        if lam < 1e-18:
            lam = 1e-18
        A = gram + lam * np.eye(p, dtype=gram.dtype)
        try:
            return np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            return np.linalg.lstsq(A, b, rcond=None)[0]

    def _stridge_fit_from_design(self, A_train, y_train, A_val, y_val, lam, thresh):
        scales = np.linalg.norm(A_train, axis=0)
        scales = np.where(scales > 0.0, scales, 1.0)

        A_tr = A_train / scales
        A_va = A_val / scales

        gram = A_tr.T @ A_tr
        b = A_tr.T @ y_train

        w = self._ridge_solve_from_gram(gram, b, lam)
        for _ in range(self.max_iter_stridge):
            small = np.abs(w) < thresh
            if not np.any(small):
                break
            big = ~small
            if np.sum(big) == 0:
                w[:] = 0.0
                break
            w_big = self._ridge_solve_from_gram(gram[np.ix_(big, big)], b[big], lam)
            w_new = np.zeros_like(w)
            w_new[big] = w_big
            w = w_new

        pred_val = A_va @ w
        resid = y_val - pred_val
        mse_val = float(np.mean(resid * resid))

        nz = np.flatnonzero(np.abs(w) > 0.0)
        k = int(nz.size)
        return w, scales, mse_val, k

    def _fit_with_params(self, M_P, M_R, y, z, lam_list, thresh_list, train_idx, val_idx):
        z_tr = z[train_idx]
        z_va = z[val_idx]

        A_train = np.hstack([M_P[train_idx] * z_tr[:, None], M_R[train_idx]])
        A_val = np.hstack([M_P[val_idx] * z_va[:, None], M_R[val_idx]])

        best = None
        n_val = max(1, len(val_idx))
        eps = 1e-30
        logn = float(np.log(n_val + 1.0))

        for lam in lam_list:
            for thresh in thresh_list:
                w_norm, scales, mse_val, k = self._stridge_fit_from_design(
                    A_train, y[train_idx], A_val, y[val_idx], lam, thresh
                )
                obj = n_val * float(np.log(mse_val + eps)) + k * logn
                if best is None or obj < best["obj"]:
                    best = {
                        "obj": obj,
                        "mse_val": mse_val,
                        "k": k,
                        "lam": float(lam),
                        "thresh": float(thresh),
                        "w_norm": w_norm,
                        "scales": scales,
                    }
        return best

    def _refit_full(self, M_P, M_R, y, z, lam, thresh):
        A_full = np.hstack([M_P * z[:, None], M_R])

        scales = np.linalg.norm(A_full, axis=0)
        scales = np.where(scales > 0.0, scales, 1.0)
        A_n = A_full / scales

        gram = A_n.T @ A_n
        b = A_n.T @ y

        w = self._ridge_solve_from_gram(gram, b, lam)
        for _ in range(self.max_iter_stridge):
            small = np.abs(w) < thresh
            if not np.any(small):
                break
            big = ~small
            if np.sum(big) == 0:
                w[:] = 0.0
                break
            w_big = self._ridge_solve_from_gram(gram[np.ix_(big, big)], b[big], lam)
            w_new = np.zeros_like(w)
            w_new[big] = w_big
            w = w_new

        nz = np.flatnonzero(np.abs(w) > 0.0)

        if nz.size > self.max_terms:
            top = nz[np.argsort(np.abs(w[nz]))[::-1][: self.max_terms]]
            keep = np.sort(top)
        else:
            keep = nz

        if keep.size == 0:
            w_full = np.zeros(A_full.shape[1], dtype=np.float64)
            return w_full, A_full

        A_sel = A_full[:, keep]
        w_sel = np.linalg.lstsq(A_sel, y, rcond=None)[0]
        w_full = np.zeros(A_full.shape[1], dtype=np.float64)
        w_full[keep] = w_sel

        maxabs = float(np.max(np.abs(w_full))) if w_full.size else 0.0
        if maxabs > 0:
            tiny = np.abs(w_full) < (1e-12 * maxabs)
            w_full[tiny] = 0.0

        return w_full, A_full

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        try:
            X = np.asarray(X, dtype=np.float64)
            y = np.asarray(y, dtype=np.float64).reshape(-1)
            n, d = X.shape
            if d != 4:
                raise ValueError("Expected X shape (n, 4)")

            rng = np.random.default_rng(self.random_state)
            idx = np.arange(n)
            rng.shuffle(idx)
            n_train = max(2, int(0.8 * n))
            train_idx = idx[:n_train]
            val_idx = idx[n_train:] if n_train < n else idx[: max(1, n // 5)]

            var_names = ["x1", "x2", "x3", "x4"]
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]

            # Polynomial bases
            exps_P = self._generate_exponents(4, 4)  # up to degree 4
            exps_R = self._generate_exponents(4, 2)  # up to degree 2

            max_deg_P = 4
            max_deg_R = 2

            pows = []
            for i in range(4):
                xi = X[:, i]
                pw = [np.ones_like(xi)]
                for e in range(1, max_deg_P + 1):
                    pw.append(pw[-1] * xi)
                pows.append(pw)

            def build_monomials(exps, max_deg):
                M = np.empty((n, len(exps)), dtype=np.float64)
                for j, e in enumerate(exps):
                    col = np.ones(n, dtype=np.float64)
                    for i in range(4):
                        ei = e[i]
                        if ei:
                            if ei <= max_deg:
                                col *= pows[i][ei]
                            else:
                                col *= X[:, i] ** ei
                    M[:, j] = col
                return M

            M_P = build_monomials(exps_P, max_deg_P)
            M_R = build_monomials(exps_R, max_deg_R)

            monom_P_strs = [self._monomial_str(e, var_names) for e in exps_P]
            monom_R_strs = [self._monomial_str(e, var_names) for e in exps_R]

            # Candidate damping forms
            np.seterr(over="ignore", under="ignore", invalid="ignore")

            bases = []
            base_exprs = []

            q1 = x1 * x1 + x2 * x2 + x3 * x3 + x4 * x4
            bases.append(q1)
            base_exprs.append("x1**2 + x2**2 + x3**2 + x4**2")

            q2 = (x1 + x2) ** 2 + (x3 + x4) ** 2
            bases.append(q2)
            base_exprs.append("(x1 + x2)**2 + (x3 + x4)**2")

            q3 = (x1 + x3) ** 2 + (x2 + x4) ** 2
            bases.append(q3)
            base_exprs.append("(x1 + x3)**2 + (x2 + x4)**2")

            q4 = (x1 + x4) ** 2 + (x2 + x3) ** 2
            bases.append(q4)
            base_exprs.append("(x1 + x4)**2 + (x2 + x3)**2")

            q5 = (x1 + x2 + x3 + x4) ** 2
            bases.append(q5)
            base_exprs.append("(x1 + x2 + x3 + x4)**2")

            q6 = (x1 - x2) ** 2 + (x3 - x4) ** 2
            bases.append(q6)
            base_exprs.append("(x1 - x2)**2 + (x3 - x4)**2")

            s_values = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
            candidates = []

            for bi in range(len(bases)):
                for s in s_values:
                    candidates.append(("base", bi, float(s), None))

            # Diagonal quadratic damping: q = sum si*xi^2
            diag_seeds = [
                np.array([0.0, 0.0, 0.0, 0.0]),
                np.array([1.0, 1.0, 1.0, 1.0]),
                np.array([0.5, 0.5, 1.0, 1.0]),
                np.array([1.0, 1.0, 0.5, 0.5]),
                np.array([2.0, 2.0, 1.0, 1.0]),
                np.array([1.0, 1.0, 2.0, 2.0]),
                np.array([0.5, 1.0, 0.5, 1.0]),
                np.array([1.0, 0.5, 1.0, 0.5]),
            ]
            for _ in range(10):
                diag_seeds.append(rng.uniform(0.0, 3.0, size=4))
            for sv in diag_seeds:
                candidates.append(("diag", None, None, sv.astype(np.float64)))

            lam_list = [1e-12, 1e-8, 1e-5]
            thresh_list = [1e-6, 1e-4, 1e-3, 1e-2]

            best_global = None

            for kind, bi, s, sv in candidates:
                if kind == "base":
                    if s == 0.0:
                        q = np.zeros(n, dtype=np.float64)
                        q_expr = "0"
                    else:
                        q = s * bases[bi]
                        if abs(s - 1.0) < 1e-15:
                            q_expr = f"({base_exprs[bi]})"
                        else:
                            q_expr = f"({self._format_float(s)})*({base_exprs[bi]})"
                else:
                    sv = np.asarray(sv, dtype=np.float64)
                    q = sv[0] * (x1 * x1) + sv[1] * (x2 * x2) + sv[2] * (x3 * x3) + sv[3] * (x4 * x4)
                    parts = []
                    if abs(sv[0]) > 1e-15:
                        parts.append(f"({self._format_float(sv[0])})*x1**2")
                    if abs(sv[1]) > 1e-15:
                        parts.append(f"({self._format_float(sv[1])})*x2**2")
                    if abs(sv[2]) > 1e-15:
                        parts.append(f"({self._format_float(sv[2])})*x3**2")
                    if abs(sv[3]) > 1e-15:
                        parts.append(f"({self._format_float(sv[3])})*x4**2")
                    q_expr = " + ".join(parts) if parts else "0"

                z = np.exp(-q)
                cand_best = self._fit_with_params(M_P, M_R, y, z, lam_list, thresh_list, train_idx, val_idx)
                if cand_best is None:
                    continue

                # Slight preference for simpler expressions if objectives tie
                obj = cand_best["obj"]
                if best_global is None or obj < best_global["obj"] - 1e-12:
                    best_global = {
                        "obj": obj,
                        "mse_val": cand_best["mse_val"],
                        "k": cand_best["k"],
                        "lam": cand_best["lam"],
                        "thresh": cand_best["thresh"],
                        "kind": kind,
                        "bi": bi,
                        "s": s,
                        "sv": sv,
                        "q_expr": q_expr,
                    }

            if best_global is None:
                raise RuntimeError("Model selection failed")

            # Build final z and refit on full data
            kind = best_global["kind"]
            if kind == "base":
                s = best_global["s"]
                bi = best_global["bi"]
                if s == 0.0:
                    q = np.zeros(n, dtype=np.float64)
                    q_expr = "0"
                else:
                    q = s * bases[bi]
                    if abs(s - 1.0) < 1e-15:
                        q_expr = f"({base_exprs[bi]})"
                    else:
                        q_expr = f"({self._format_float(s)})*({base_exprs[bi]})"
            else:
                sv = np.asarray(best_global["sv"], dtype=np.float64)
                q = sv[0] * (x1 * x1) + sv[1] * (x2 * x2) + sv[2] * (x3 * x3) + sv[3] * (x4 * x4)
                parts = []
                if abs(sv[0]) > 1e-15:
                    parts.append(f"({self._format_float(sv[0])})*x1**2")
                if abs(sv[1]) > 1e-15:
                    parts.append(f"({self._format_float(sv[1])})*x2**2")
                if abs(sv[2]) > 1e-15:
                    parts.append(f"({self._format_float(sv[2])})*x3**2")
                if abs(sv[3]) > 1e-15:
                    parts.append(f"({self._format_float(sv[3])})*x4**2")
                q_expr = " + ".join(parts) if parts else "0"

            z = np.exp(-q)
            w_full, A_full = self._refit_full(M_P, M_R, y, z, best_global["lam"], best_global["thresh"])

            pP = M_P.shape[1]
            wP = w_full[:pP]
            wR = w_full[pP:]

            nzP = np.flatnonzero(np.abs(wP) > 0.0)
            nzR = np.flatnonzero(np.abs(wR) > 0.0)

            P_expr = self._build_expr_from_terms(wP, monom_P_strs, nzP)
            R_expr = self._build_expr_from_terms(wR, monom_R_strs, nzR)

            use_exp = (q_expr != "0") and (P_expr != "0") and (np.any(np.abs(wP) > 0.0))

            if use_exp:
                damp_expr = f"exp(-({q_expr}))*({P_expr})"
            else:
                damp_expr = P_expr

            if R_expr != "0" and damp_expr != "0":
                expression = f"({damp_expr}) + ({R_expr})"
            elif R_expr != "0":
                expression = R_expr
            else:
                expression = damp_expr

            # Predictions
            pred = A_full @ w_full
            pred = np.asarray(pred, dtype=np.float64)

            complexity = int((1 if use_exp else 0) + int(nzP.size) + int(nzR.size))

            return {
                "expression": expression,
                "predictions": pred.tolist(),
                "details": {"complexity": complexity},
            }
        except Exception:
            X = np.asarray(X, dtype=np.float64)
            y = np.asarray(y, dtype=np.float64).reshape(-1)
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
            A = np.column_stack([x1, x2, x3, x4, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c, d, e = coeffs
            expression = (
                f"({self._format_float(a)})*x1 + ({self._format_float(b)})*x2 + "
                f"({self._format_float(c)})*x3 + ({self._format_float(d)})*x4 + "
                f"({self._format_float(e)})"
            )
            pred = (a * x1 + b * x2 + c * x3 + d * x4 + e).astype(np.float64)
            return {
                "expression": expression,
                "predictions": pred.tolist(),
                "details": {"complexity": 5},
            }