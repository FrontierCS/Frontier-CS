import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.max_terms = kwargs.get("max_terms", 24)
        self.max_degree_poly = kwargs.get("max_degree_poly", 2)
        self.extra_degree_nogauss = kwargs.get("extra_degree_nogauss", 3)
        self.ridge = kwargs.get("ridge", 1e-8)
        self.tol_rel = kwargs.get("tol_rel", 1e-9)
        self.random_state = kwargs.get("random_state", 42)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        rng = np.random.default_rng(self.random_state)
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        n, d = X.shape
        if d != 4:
            # Handle unexpected input dimensions by simple linear baseline
            return self._baseline_linear(X, y)

        # Precompute stats
        mu = np.nanmean(X, axis=0)
        var = np.nanvar(X, axis=0) + 1e-12
        invvar = 1.0 / var

        # Build gaussian sets
        gaussians = self._build_gaussians(X, mu, invvar)

        # Build monomial exponent sets
        exps_deg2 = self._generate_monomial_exponents(self.max_degree_poly)
        exps_deg3 = self._generate_monomial_exponents(self.extra_degree_nogauss)
        exps_deg3_only = [e for e in exps_deg3 if sum(e) > self.max_degree_poly]

        # Precompute powers up to degree 3
        x = [X[:, i] for i in range(4)]
        xpows = [[np.ones(n), x[i], x[i] * x[i], x[i] * x[i] * x[i]] for i in range(4)]

        # Build feature matrix and meta
        F, meta = self._build_features(X, gaussians, exps_deg2, exps_deg3_only, xpows)

        # If F is empty or degenerate, fallback
        if F.shape[1] == 0 or not np.all(np.isfinite(F)):
            return self._baseline_linear(X, y)

        # Orthogonal Matching Pursuit with ridge refit
        selected_idx, coefs = self._omp(F, y, self.max_terms, self.ridge, self.tol_rel)

        # If OMP fails, fallback
        if len(selected_idx) == 0 or coefs.size == 0:
            return self._baseline_linear(X, y)

        # Predictions
        y_pred = F[:, selected_idx] @ coefs

        # Build expression string, grouped by gaussian
        expression = self._build_expression(selected_idx, coefs, meta, gaussians, mu)

        # Final safety: if expression empty, fallback
        if not isinstance(expression, str) or len(expression.strip()) == 0:
            return self._baseline_linear(X, y)

        return {
            "expression": expression,
            "predictions": y_pred.tolist(),
            "details": {"n_terms": int(len(selected_idx))}
        }

    def _baseline_linear(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        n = X.shape[0]
        A = np.column_stack([X, np.ones(n)])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except Exception:
            coeffs = np.zeros(X.shape[1] + 1)
            coeffs[-1] = np.mean(y) if y.size > 0 else 0.0
        a, b, c, d, e = coeffs
        expression = f"({self._fmt(a)})*x1 + ({self._fmt(b)})*x2 + ({self._fmt(c)})*x3 + ({self._fmt(d)})*x4 + ({self._fmt(e)})"
        y_pred = A @ coeffs
        return {
            "expression": expression,
            "predictions": y_pred.tolist(),
            "details": {"n_terms": 5}
        }

    def _fmt(self, v, digits=12):
        # Format float with a reasonable number of significant digits
        try:
            if not np.isfinite(v):
                return "0"
        except Exception:
            return "0"
        return f"{float(v):.{digits}g}"

    def _generate_monomial_exponents(self, max_degree):
        exps = []
        for e1 in range(max_degree + 1):
            for e2 in range(max_degree + 1):
                for e3 in range(max_degree + 1):
                    for e4 in range(max_degree + 1):
                        if e1 + e2 + e3 + e4 <= max_degree:
                            exps.append((e1, e2, e3, e4))
        return exps

    def _monomial_val(self, e, xpows):
        e1, e2, e3, e4 = e
        return xpows[0][e1] * xpows[1][e2] * xpows[2][e3] * xpows[3][e4]

    def _monomial_str(self, e):
        parts = []
        exps = [("x1", e[0]), ("x2", e[1]), ("x3", e[2]), ("x4", e[3])]
        for var, powe in exps:
            if powe == 0:
                continue
            elif powe == 1:
                parts.append(var)
            else:
                parts.append(f"{var}**{powe}")
        if not parts:
            return "1"
        return "*".join(parts)

    def _build_gaussians(self, X, mu, invvar):
        n, d = X.shape
        x_centered = X - mu

        # Precompute squares
        x2 = X * X
        xc2 = x_centered * x_centered

        # Define weight sets
        gaussians = []

        # None (no gaussian)
        gaussians.append({
            "type": "none",
            "weights": np.zeros(4),
            "centered": False,
            "values": np.ones(n),
            "expr": "",
        })

        # Iso alphas
        iso_alphas = [0.5, 1.0]
        for a in iso_alphas:
            w = np.array([a, a, a, a], dtype=float)
            s = w[0]*x2[:, 0] + w[1]*x2[:, 1] + w[2]*x2[:, 2] + w[3]*x2[:, 3]
            gval = np.exp(-s)
            expr = self._gaussian_expr_str(weights=w, mu=np.zeros(4), centered=False)
            gaussians.append({
                "type": "iso",
                "weights": w,
                "centered": False,
                "values": gval,
                "expr": expr,
            })

        # Anisotropic scaled by invvar, both centered and uncentered
        scales = [0.5, 1.0]
        for k in scales:
            w = k * invvar
            s_unc = w[0]*x2[:, 0] + w[1]*x2[:, 1] + w[2]*x2[:, 2] + w[3]*x2[:, 3]
            g_unc = np.exp(-s_unc)
            expr_unc = self._gaussian_expr_str(weights=w, mu=np.zeros(4), centered=False)
            gaussians.append({
                "type": "anis",
                "weights": w,
                "centered": False,
                "values": g_unc,
                "expr": expr_unc,
            })

            s_cen = w[0]*xc2[:, 0] + w[1]*xc2[:, 1] + w[2]*xc2[:, 2] + w[3]*xc2[:, 3]
            g_cen = np.exp(-s_cen)
            expr_cen = self._gaussian_expr_str(weights=w, mu=mu, centered=True)
            gaussians.append({
                "type": "anis",
                "weights": w,
                "centered": True,
                "values": g_cen,
                "expr": expr_cen,
            })

        return gaussians

    def _gaussian_expr_str(self, weights, mu, centered):
        # Build string: exp(-(w1*(x1 - mu1)**2 + ...))
        terms = []
        for i, wi in enumerate(weights):
            if abs(wi) < 1e-15:
                continue
            var = f"x{i+1}"
            if centered:
                mui = self._fmt(mu[i], digits=8)
                # (x - mu)**2
                term = f"{self._fmt(wi)}*({var} - {mui})**2"
            else:
                term = f"{self._fmt(wi)}*{var}**2"
            terms.append(term)
        if not terms:
            return "1"
        inner = " + ".join(terms)
        return f"exp(-({inner}))"

    def _build_features(self, X, gaussians, exps_deg2, exps_deg3_only, xpows):
        n = X.shape[0]
        cols = []
        meta = []

        # For each gaussian, include monomials up to degree 2
        for gi, g in enumerate(gaussians):
            gv = g["values"]
            for e in exps_deg2:
                monval = self._monomial_val(e, xpows)
                cols.append(monval * gv)
                meta.append({"gi": gi, "e": e})

        # For the no-gaussian case, include extra degree 3 monomials
        gi0 = 0  # index 0 is 'none'
        g0v = gaussians[gi0]["values"]
        for e in exps_deg3_only:
            monval = self._monomial_val(e, xpows)
            cols.append(monval * g0v)
            meta.append({"gi": gi0, "e": e})

        if len(cols) == 0:
            F = np.zeros((n, 0))
        else:
            F = np.column_stack(cols)
        return F, meta

    def _omp(self, F, y, max_terms, ridge, tol_rel):
        n, m = F.shape
        # Normalize columns for selection step
        col_norms = np.linalg.norm(F, axis=0) + 1e-20
        Fz = F / col_norms

        resid = y.copy()
        active = []
        used = np.zeros(m, dtype=bool)

        sse_prev = float(np.dot(resid, resid))
        y_var = float(np.dot(y - np.mean(y), y - np.mean(y))) + 1e-20
        tol_abs = max(tol_rel * y_var, 1e-18)

        for _ in range(min(max_terms, m)):
            c = Fz.T @ resid
            c[used] = 0.0
            j = int(np.argmax(np.abs(c)))
            if not np.isfinite(c[j]) or abs(c[j]) < 1e-14:
                break
            used[j] = True
            active.append(j)

            # Refit on original features with ridge
            FA = F[:, active]
            w = self._ridge_solve(FA, y, ridge)

            resid = y - FA @ w
            sse = float(np.dot(resid, resid))
            if sse_prev - sse < tol_abs:
                break
            sse_prev = sse

        if len(active) == 0:
            return [], np.array([])

        FA = F[:, active]
        w = self._ridge_solve(FA, y, ridge)
        return active, w

    def _ridge_solve(self, A, b, ridge):
        # Solve (A^T A + ridge I) w = A^T b
        AtA = A.T @ A
        k = AtA.shape[0]
        if ridge > 0:
            AtA = AtA + ridge * np.eye(k)
        Atb = A.T @ b
        try:
            w = np.linalg.solve(AtA, Atb)
        except np.linalg.LinAlgError:
            w = np.linalg.lstsq(A, b, rcond=None)[0]
        return w

    def _build_expression(self, selected_idx, coefs, meta, gaussians, mu):
        # Group terms by gaussian index
        groups = {}
        for idx, coef in zip(selected_idx, coefs):
            if not np.isfinite(coef):
                continue
            info = meta[idx]
            gi = info["gi"]
            e = tuple(info["e"])
            if gi not in groups:
                groups[gi] = {}
            groups[gi][e] = groups[gi].get(e, 0.0) + float(coef)

        # Build polynomial expressions for each group
        group_exprs = []
        # Sort groups to put 'none' first if present
        gis_sorted = sorted(groups.keys())
        if 0 in gis_sorted:
            gis_sorted.remove(0)
            gis_sorted = [0] + gis_sorted

        for gi in gis_sorted:
            terms = groups[gi]
            # Drop near-zero terms
            terms = {e: c for e, c in terms.items() if abs(c) > 1e-12}
            if not terms:
                continue

            # Build polynomial string
            poly_terms = []
            # Order terms by total degree then lexicographically
            def deg(e):
                return sum(e)
            for e in sorted(terms.keys(), key=lambda t: (deg(t), t)):
                c = terms[e]
                mon = self._monomial_str(e)
                cstr = self._fmt(c)
                if mon == "1":
                    term = f"({cstr})"
                else:
                    term = f"({cstr})*{mon}"
                poly_terms.append(term)

            if not poly_terms:
                continue
            poly_expr = " + ".join(poly_terms)

            gexpr = gaussians[gi]["expr"]
            if gexpr == "" or gexpr == "1":
                grp_expr = f"({poly_expr})"
            else:
                grp_expr = f"({poly_expr})*{gexpr}"
            group_exprs.append(grp_expr)

        if not group_exprs:
            return "0"

        expression = " + ".join(group_exprs)
        return expression