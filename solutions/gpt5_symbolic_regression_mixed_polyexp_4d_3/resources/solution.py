import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.max_terms = int(kwargs.get("max_terms", 14))
        self.max_poly_degree = int(kwargs.get("max_poly_degree", 4))
        self.single_max_degree = int(kwargs.get("single_max_degree", 5))
        self.random_state = int(kwargs.get("random_state", 42))
        self.min_improvement = float(kwargs.get("min_improvement", 1e-6))
        self.normalize_features = True

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        n, d = X.shape
        rng = np.random.RandomState(self.random_state)

        # Build feature dictionary
        Phi, features = self._build_feature_matrix(X)

        # Normalize feature columns for stable selection
        col_norms = np.sqrt(np.mean(Phi**2, axis=0) + 1e-18)
        if self.normalize_features:
            Phi_norm = Phi / col_norms
        else:
            Phi_norm = Phi.copy()

        # Orthogonal Matching Pursuit for sparsity
        k_max = min(self.max_terms * 2, Phi_norm.shape[1])
        sel_idx, coefs_norm = self._omp(Phi_norm, y, k_max)

        if len(sel_idx) == 0:
            c0 = float(np.mean(y))
            expression = f"{self._fmt(c0)}"
            preds = np.full(n, c0)
            return {
                "expression": expression,
                "predictions": preds.tolist(),
                "details": {}
            }

        # Keep top 'max_terms' by absolute normalized coefficients
        order = np.argsort(-np.abs(coefs_norm))
        keep = order[: self.max_terms]
        sel_idx = [sel_idx[i] for i in keep]

        # Refit least squares on selected features (un-normalized)
        Phi_sel = Phi[:, sel_idx]
        coef_sel, _, _, _ = np.linalg.lstsq(Phi_sel, y, rcond=None)

        # Optional pruning of near-zero coefficients
        abs_coef = np.abs(coef_sel)
        if abs_coef.size > 0:
            thresh = np.max(abs_coef) * 1e-8
            mask = abs_coef >= thresh
            if not np.all(mask):
                sel_idx = [idx for idx, m in zip(sel_idx, mask) if m]
                Phi_sel = Phi[:, sel_idx]
                coef_sel = coef_sel[mask]

        # Final predictions
        preds = Phi_sel @ coef_sel

        # Build expression string
        terms = []
        for idx, c in zip(sel_idx, coef_sel):
            if abs(c) < 1e-14:
                continue
            term_str = self._feature_to_string(features[idx])
            # Combine coefficient and term
            if term_str == "1":
                term_full = f"{self._fmt(c)}"
            else:
                term_full = f"{self._fmt(c)}*{term_str}"
            terms.append(term_full)

        if not terms:
            # Fallback
            c0 = float(np.mean(y))
            expression = f"{self._fmt(c0)}"
        else:
            # Assemble with proper sign handling
            expression = self._sum_terms_with_signs(terms)

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }

    def _build_feature_matrix(self, X):
        n, d = X.shape
        # Basic sets
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        # Scales for adaptive Gaussian widths
        r2 = x1**2 + x2**2 + x3**2 + x4**2
        r2_scale = float(np.mean(r2) + 1e-12)
        # Global alphas (including 0 for pure polynomial)
        # Choosing a range of decays relative to scale
        base_vals = [0.0, 0.25, 0.5, 1.0, 2.0]
        alphas_global = [v / r2_scale for v in base_vals]

        # Single-variable alphas (exclude 0)
        xs2 = np.maximum(np.mean(X**2, axis=0), 1e-12)
        single_base_vals = [0.5, 1.0, 2.0]
        alphas_single = [ [v / xs2[i] for v in single_base_vals] for i in range(4) ]

        features = []
        columns = []

        # Precompute exp(-alpha*r2) for all global alphas
        exp_global = [np.exp(-ag * r2) if ag != 0.0 else np.ones(n) for ag in alphas_global]

        # Generate polynomial monomials up to max degree
        mono_exps = self._generate_monomial_exponents(self.max_poly_degree)
        mono_cache = {}
        for e in mono_exps:
            mono = self._compute_monomial(X, e, cache=mono_cache)
            # For each global alpha
            for ag, eglob in zip(alphas_global, exp_global):
                col = mono * eglob
                columns.append(col)
                features.append({
                    "type": "global_poly_exp",
                    "exponents": e,
                    "alpha": ag
                })

        # Single-variable Gaussian-damped univariate polynomials
        for i in range(4):
            xi = X[:, i]
            xi2 = xi**2
            for a in alphas_single[i]:
                eg = np.exp(-a * xi2)
                for deg in range(0, self.single_max_degree + 1):
                    if deg == 0:
                        mono = np.ones(n)
                    else:
                        mono = xi**deg
                    col = mono * eg
                    columns.append(col)
                    features.append({
                        "type": "single_poly_exp",
                        "var": i,
                        "degree": deg,
                        "alpha": a
                    })

        Phi = np.column_stack(columns) if columns else np.empty((n, 0))
        return Phi, features

    def _generate_monomial_exponents(self, max_degree):
        exps = []
        # Enumerate e1+e2+e3+e4 <= max_degree
        for deg in range(0, max_degree + 1):
            for e1 in range(0, deg + 1):
                for e2 in range(0, deg - e1 + 1):
                    for e3 in range(0, deg - e1 - e2 + 1):
                        e4 = deg - e1 - e2 - e3
                        exps.append((e1, e2, e3, e4))
        return exps

    def _compute_monomial(self, X, exps, cache=None):
        if cache is None:
            cache = {}
        key = tuple(exps)
        if key in cache:
            return cache[key]
        res = np.ones(X.shape[0])
        for i, power in enumerate(exps):
            if power == 0:
                continue
            res = res * (X[:, i] ** power)
        cache[key] = res
        return res

    def _omp(self, Phi, y, k_max):
        n, m = Phi.shape
        if m == 0:
            return [], np.array([])
        residual = y.copy()
        selected = []
        coefs = []
        available = np.ones(m, dtype=bool)
        prev_error = np.mean(residual**2)

        for _ in range(k_max):
            # Correlations with available features
            # Phi is assumed normalized by column RMS; still compute correlations directly
            corr = Phi.T @ residual
            corr_abs = np.abs(corr)
            corr_abs[~available] = -np.inf
            j = int(np.argmax(corr_abs))
            if not np.isfinite(corr_abs[j]):
                break
            available[j] = False
            selected.append(j)

            # Refit coefficients using least squares on selected subset
            Phi_sel = Phi[:, selected]
            coef, _, _, _ = np.linalg.lstsq(Phi_sel, y, rcond=None)
            coefs = coef

            # Update residual
            residual = y - Phi_sel @ coef
            curr_error = np.mean(residual**2)

            # Early stopping if little improvement
            if prev_error - curr_error < self.min_improvement * max(prev_error, 1.0):
                break
            prev_error = curr_error

        # If nothing selected, return empty
        if len(selected) == 0:
            return [], np.array([])

        # Final coefficients (normalized space) for selected features
        Phi_sel = Phi[:, selected]
        coef, _, _, _ = np.linalg.lstsq(Phi_sel, y, rcond=None)
        return selected, coef

    def _feature_to_string(self, feat):
        if feat["type"] == "global_poly_exp":
            exps = feat["exponents"]
            alpha = feat["alpha"]
            mono_str = self._monomial_string(exps)
            if alpha == 0.0:
                if mono_str == "":
                    return "1"
                return mono_str
            r2_str = "(x1**2 + x2**2 + x3**2 + x4**2)"
            exp_str = f"exp(-{self._fmt(alpha)}*{r2_str})"
            if mono_str == "":
                return exp_str
            else:
                return f"{mono_str}*{exp_str}"
        elif feat["type"] == "single_poly_exp":
            i = feat["var"]
            deg = feat["degree"]
            alpha = feat["alpha"]
            xi = f"x{i+1}"
            mono = "1" if deg == 0 else (xi if deg == 1 else f"{xi}**{deg}")
            exp_str = f"exp(-{self._fmt(alpha)}*({xi}**2))"
            if mono == "1":
                return exp_str
            else:
                return f"{mono}*{exp_str}"
        else:
            return "1"

    def _monomial_string(self, exps):
        parts = []
        varnames = ["x1", "x2", "x3", "x4"]
        for v, p in zip(varnames, exps):
            if p == 0:
                continue
            elif p == 1:
                parts.append(v)
            else:
                parts.append(f"{v}**{p}")
        return "*".join(parts)

    def _fmt(self, x):
        # Format float with reasonable precision
        if np.isfinite(x):
            return f"{float(x):.12g}"
        else:
            return "0"

    def _sum_terms_with_signs(self, terms):
        # terms: list of strings like "c*term" where c may be negative
        expr = ""
        for i, t in enumerate(terms):
            # Extract coefficient sign if possible
            # Split at first '*' to get coefficient
            coef_str = None
            rest = None
            if "*" in t:
                coef_str, rest = t.split("*", 1)
            else:
                coef_str, rest = t, None
            try:
                coef_val = float(coef_str)
                sign = "-" if coef_val < 0 else "+"
                coef_abs = self._fmt(abs(coef_val))
                if rest is None or rest == "":
                    term_body = coef_abs
                else:
                    term_body = f"{coef_abs}*{rest}"
            except Exception:
                # Fallback: cannot parse numeric coefficient reliably
                sign = "+"
                term_body = t

            if i == 0:
                if sign == "-":
                    expr += f"-{term_body}"
                else:
                    expr += term_body
            else:
                if sign == "-":
                    expr += f" - {term_body}"
                else:
                    expr += f" + {term_body}"
        return expr if expr else "0"
