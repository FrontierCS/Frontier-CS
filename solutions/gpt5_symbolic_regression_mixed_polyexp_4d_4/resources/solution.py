import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.max_poly_deg = kwargs.get("max_poly_deg", 3)
        self.max_poly_deg_aniso = kwargs.get("max_poly_deg_aniso", 2)
        self.max_terms = kwargs.get("max_terms", 14)
        self.ridge_alpha = kwargs.get("ridge_alpha", 1e-8)
        self.include_intercept = kwargs.get("include_intercept", True)
        self.random_state = kwargs.get("random_state", 42)

    def _format_float(self, x):
        return f"{x:.12g}"

    def _build_monomials(self, X, maxdeg):
        n = X.shape[0]
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        # Precompute powers 0..3
        def powers(v):
            return [np.ones_like(v), v, v * v, v * v * v]
        p1 = powers(x1)
        p2 = powers(x2)
        p3 = powers(x3)
        p4 = powers(x4)

        monomials = []
        # Iterate exponents e1..e4 with sum <= maxdeg
        for e1 in range(0, maxdeg + 1):
            for e2 in range(0, maxdeg + 1 - e1):
                for e3 in range(0, maxdeg + 1 - e1 - e2):
                    e4 = 0
                    while e1 + e2 + e3 + e4 <= maxdeg:
                        degsum = e1 + e2 + e3 + e4
                        # compose string
                        parts = []
                        if e1 > 0:
                            if e1 == 1:
                                parts.append("x1")
                            else:
                                parts.append(f"x1**{e1}")
                        if e2 > 0:
                            if e2 == 1:
                                parts.append("x2")
                            else:
                                parts.append(f"x2**{e2}")
                        if e3 > 0:
                            if e3 == 1:
                                parts.append("x3")
                            else:
                                parts.append(f"x3**{e3}")
                        if e4 > 0:
                            if e4 == 1:
                                parts.append("x4")
                            else:
                                parts.append(f"x4**{e4}")
                        mon_str = " * ".join(parts) if parts else "1"

                        vec = p1[e1] * p2[e2] * p3[e3] * p4[e4]
                        monomials.append({
                            "deg": degsum,
                            "exps": (e1, e2, e3, e4),
                            "name": mon_str,
                            "vec": vec.astype(np.float64, copy=False)
                        })
                        e4 += 1
                        if e4 > maxdeg:
                            break
        return monomials

    def _build_envelopes(self, X):
        # Build envelope functions of form exp(-(a1*x1**2 + a2*x2**2 + a3*x3**2 + a4*x4**2))
        # Include identity envelope "1"
        n = X.shape[0]
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        x1sq = x1 * x1
        x2sq = x2 * x2
        x3sq = x3 * x3
        x4sq = x4 * x4

        # Typical scale to set gamma ranges
        s2 = float(np.mean(x1sq + x2sq + x3sq + x4sq)) + 1e-12

        iso_scales = np.array([0.2, 0.5, 1.0, 2.0, 5.0], dtype=np.float64) / s2
        aniso_bases = np.array([0.5, 1.0, 2.0], dtype=np.float64) / s2

        envelopes = []
        # Identity envelope
        envelopes.append({
            "name": "1",
            "vec": np.ones(n, dtype=np.float64),
            "type": "none",
            "gvec": (0.0, 0.0, 0.0, 0.0)
        })

        # Isotropic
        for g in iso_scales:
            # exp(-g*(x1**2 + x2**2 + x3**2 + x4**2))
            argvec = g * (x1sq + x2sq + x3sq + x4sq)
            vec = np.exp(-argvec)
            g1 = self._format_float(g)
            env_name = f"exp(-({g1}*x1**2 + {g1}*x2**2 + {g1}*x3**2 + {g1}*x4**2))"
            envelopes.append({
                "name": env_name,
                "vec": vec,
                "type": "iso",
                "gvec": (g, g, g, g)
            })

        # Anisotropic: for each base gamma, choose subsets of variables to apply it to
        # We exclude the empty mask
        seen_gvecs = set()
        for gb in aniso_bases:
            for mask in range(1, 1 << 4):
                g1 = gb if (mask & 1) else 0.0
                g2 = gb if (mask & 2) else 0.0
                g3 = gb if (mask & 4) else 0.0
                g4 = gb if (mask & 8) else 0.0
                gvec = (float(g1), float(g2), float(g3), float(g4))
                if gvec in seen_gvecs:
                    continue
                seen_gvecs.add(gvec)
                argvec = g1 * x1sq + g2 * x2sq + g3 * x3sq + g4 * x4sq
                vec = np.exp(-argvec)
                parts = []
                if g1 != 0.0:
                    parts.append(f"{self._format_float(g1)}*x1**2")
                if g2 != 0.0:
                    parts.append(f"{self._format_float(g2)}*x2**2")
                if g3 != 0.0:
                    parts.append(f"{self._format_float(g3)}*x3**2")
                if g4 != 0.0:
                    parts.append(f"{self._format_float(g4)}*x4**2")
                inside = " + ".join(parts) if parts else "0"
                env_name = f"exp(-({inside}))"
                envelopes.append({
                    "name": env_name,
                    "vec": vec,
                    "type": "anis",
                    "gvec": gvec
                })
        return envelopes

    def _generate_features(self, X):
        # Create features as monomials multiplied by envelopes.
        # - For env "none": monomials up to degree self.max_poly_deg
        # - For isotropic envelopes: monomials up to degree self.max_poly_deg
        # - For anisotropic envelopes: monomials up to degree self.max_poly_deg_aniso
        monomials_deg3 = self._build_monomials(X, self.max_poly_deg)
        monomials_deg2 = self._build_monomials(X, self.max_poly_deg_aniso)
        envelopes = self._build_envelopes(X)

        # Map from feature string to column vector (to avoid duplicates)
        names = []
        cols = []

        # Utility to add feature
        def add_feature(monom, env):
            if env["name"] == "1":
                fe_name = monom["name"]
                vec = monom["vec"]
            elif monom["name"] == "1":
                fe_name = env["name"]
                vec = env["vec"]
            else:
                fe_name = f"({monom['name']})*({env['name']})"
                vec = monom["vec"] * env["vec"]
            # skip non-finite or zero-variance columns
            if not np.all(np.isfinite(vec)):
                return
            if np.max(np.abs(vec)) < 1e-15:
                return
            names.append(fe_name)
            cols.append(vec)

        for env in envelopes:
            if env["type"] == "none":
                # pure monomials up to deg3
                for mon in monomials_deg3:
                    add_feature(mon, env)
            elif env["type"] == "iso":
                for mon in monomials_deg3:
                    add_feature(mon, env)
            else:  # anis
                for mon in monomials_deg2:
                    add_feature(mon, env)

        # Convert to array
        if len(cols) == 0:
            Z = np.zeros((X.shape[0], 1), dtype=np.float64)
            names = ["1"]
        else:
            Z = np.column_stack(cols).astype(np.float64, copy=False)
        return Z, names

    def _omp_ridge(self, Z, y, names, max_terms, alpha, include_intercept=True):
        n, m = Z.shape
        # Normalize columns for selection step
        col_norms = np.sqrt(np.sum(Z * Z, axis=0)) + 1e-12

        selected = []
        # Start with intercept if present
        if include_intercept:
            # try finding index of constant "1"
            try:
                idx_bias = names.index("1")
            except ValueError:
                idx_bias = None
            if idx_bias is not None:
                selected.append(idx_bias)

        # Initialize
        if len(selected) > 0:
            Zs = Z[:, selected]
            AtA = Zs.T @ Zs
            if alpha > 0:
                AtA = AtA + alpha * np.eye(len(selected))
            Aty = Zs.T @ y
            try:
                coefs = np.linalg.solve(AtA, Aty)
            except np.linalg.LinAlgError:
                coefs = np.linalg.lstsq(Zs, y, rcond=None)[0]
            resid = y - Zs @ coefs
            best_sse = float(np.dot(resid, resid))
        else:
            coefs = np.array([])
            resid = y.copy()
            best_sse = float(np.dot(resid, resid))

        max_iters = min(max_terms, m)
        for _ in range(max_iters - len(selected)):
            # Correlations
            corr = (Z.T @ resid) / col_norms
            # Mask out already selected
            corr[selected] = 0.0
            j = int(np.argmax(np.abs(corr)))
            if j in selected:
                break
            selected.append(j)
            # Refit ridge on selected set
            Zs = Z[:, selected]
            AtA = Zs.T @ Zs
            if alpha > 0:
                AtA = AtA + alpha * np.eye(len(selected))
            Aty = Zs.T @ y
            try:
                coefs = np.linalg.solve(AtA, Aty)
            except np.linalg.LinAlgError:
                coefs = np.linalg.lstsq(Zs, y, rcond=None)[0]
            resid = y - Zs @ coefs
            sse = float(np.dot(resid, resid))
            # Early stopping if improvement is tiny
            if best_sse - sse < 1e-10 * (1.0 + best_sse):
                best_sse = sse
                break
            best_sse = sse

        # Final pruning: drop near-zero coefficients
        if len(selected) > 0:
            mask_nz = np.abs(coefs) > 1e-10
            if not np.all(mask_nz):
                selected = [j for k, j in enumerate(selected) if mask_nz[k]]
                if selected:
                    Zs = Z[:, selected]
                    AtA = Zs.T @ Zs
                    if alpha > 0:
                        AtA = AtA + alpha * np.eye(len(selected))
                    Aty = Zs.T @ y
                    try:
                        coefs = np.linalg.solve(AtA, Aty)
                    except np.linalg.LinAlgError:
                        coefs = np.linalg.lstsq(Zs, y, rcond=None)[0]
                else:
                    coefs = np.array([])
                    resid = y.copy()
        return selected, coefs

    def _compose_expression(self, names, coefs):
        terms = []
        for c, name in zip(coefs, names):
            if abs(c) < 1e-12:
                continue
            cstr = self._format_float(c)
            if name == "1":
                term = cstr
            else:
                term = f"{cstr}*({name})"
            terms.append(term)
        if not terms:
            return "0"
        # Combine with + and - cleanly
        expr = terms[0]
        for t in terms[1:]:
            if t.startswith("-"):
                expr += " - " + t[1:]
            else:
                expr += " + " + t
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).ravel()
        n, d = X.shape
        if d != 4:
            raise ValueError("Expected X to have shape (n, 4).")
        # Generate features
        Z, names = self._generate_features(X)

        # Run OMP with ridge refit
        selected, coefs = self._omp_ridge(
            Z, y, names, max_terms=self.max_terms, alpha=self.ridge_alpha, include_intercept=self.include_intercept
        )

        if len(selected) == 0:
            # Fallback to simple linear regression on [x1, x2, x3, x4, 1]
            A = np.column_stack([X, np.ones(X.shape[0])])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c, d, e = coeffs
            expression = f"{self._format_float(a)}*x1 + {self._format_float(b)}*x2 + {self._format_float(c)}*x3 + {self._format_float(d)}*x4 + {self._format_float(e)}"
            preds = (A @ coeffs).tolist()
            return {"expression": expression, "predictions": preds, "details": {}}

        # Compose final expression
        sel_names = [names[j] for j in selected]
        expression = self._compose_expression(sel_names, coefs)

        # Predictions
        preds = (Z[:, selected] @ coefs).astype(np.float64, copy=False)

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }
