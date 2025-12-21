import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def _format_number(self, v, sig=12):
        if not np.isfinite(v):
            v = 0.0
        if abs(v) < 1e-12:
            v = 0.0
        s = f"{float(v):.{sig}g}"
        # Normalize -0 to 0
        if s.startswith("-0") and ("." not in s or set(s.replace("-", "").replace("0", "")) == set()):
            s = s.replace("-", "")
        return s

    def _float_from_formatted(self, v):
        return float(self._format_number(v))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        n, d = X.shape
        x1 = X[:, 0].astype(float)
        x2 = X[:, 1].astype(float)
        y = y.astype(float)

        # Precompute base features
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)

        # Candidate features: (name, array values, meta)
        feats = []
        def add_feat(name, vals, meta=None):
            feats.append((name, vals.astype(float), meta))

        # Simple univariate trig
        add_feat("sin(x1)", s1, {"type": "sin", "args": ("x1",)})
        add_feat("cos(x1)", c1, {"type": "cos", "args": ("x1",)})
        add_feat("sin(x2)", s2, {"type": "sin", "args": ("x2",)})
        add_feat("cos(x2)", c2, {"type": "cos", "args": ("x2",)})

        # Sum/difference trig
        s12 = np.sin(x1 + x2)
        s1m2 = np.sin(x1 - x2)
        c12 = np.cos(x1 + x2)
        c1m2 = np.cos(x1 - x2)
        add_feat("sin(x1 + x2)", s12, {"type": "sin", "args": ("x1", "+", "x2")})
        add_feat("sin(x1 - x2)", s1m2, {"type": "sin", "args": ("x1", "-", "x2")})
        add_feat("cos(x1 + x2)", c12, {"type": "cos", "args": ("x1", "+", "x2")})
        add_feat("cos(x1 - x2)", c1m2, {"type": "cos", "args": ("x1", "-", "x2")})

        # Pairwise products
        add_feat("sin(x1)*sin(x2)", s1 * s2, {"type": "prod", "f1": ("sin", "x1"), "f2": ("sin", "x2")})
        add_feat("sin(x1)*cos(x2)", s1 * c2, {"type": "prod", "f1": ("sin", "x1"), "f2": ("cos", "x2")})
        add_feat("cos(x1)*sin(x2)", c1 * s2, {"type": "prod", "f1": ("cos", "x1"), "f2": ("sin", "x2")})
        add_feat("cos(x1)*cos(x2)", c1 * c2, {"type": "prod", "f1": ("cos", "x1"), "f2": ("cos", "x2")})

        # Linear terms (fallback)
        add_feat("x1", x1, {"type": "var", "var": "x1"})
        add_feat("x2", x2, {"type": "var", "var": "x2"})

        names = [f[0] for f in feats]
        F = np.column_stack([f[1] for f in feats]).astype(float)

        # Helper: fit and compute BIC
        def fit_and_bic(A, y):
            if A.ndim == 1:
                A = A.reshape(-1, 1)
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            pred = A @ coeffs
            resid = y - pred
            rss = float(resid @ resid)
            k = A.shape[1]
            n = len(y)
            rss = max(rss, 1e-18)
            bic = n * np.log(rss / max(n, 1)) + k * np.log(max(n, 1))
            return coeffs, pred, bic, rss

        ones = np.ones(n, dtype=float)
        selected = []
        A_curr = ones.reshape(-1, 1)
        coeffs_curr, pred_curr, bic_curr, rss_curr = fit_and_bic(A_curr, y)

        # Forward stepwise selection using BIC
        remaining = list(range(F.shape[1]))
        bic_tol = 1e-9
        max_features = min(20, F.shape[1])

        while len(selected) < max_features and len(remaining) > 0:
            best_bic = bic_curr
            best_j = None
            best_coeffs = None
            best_pred = None
            for j in remaining:
                A_try = np.column_stack([A_curr, F[:, j]])
                c_try, p_try, b_try, _ = fit_and_bic(A_try, y)
                if b_try + bic_tol < best_bic:
                    best_bic = b_try
                    best_j = j
                    best_coeffs = c_try
                    best_pred = p_try
            if best_j is None:
                break
            # Accept best candidate
            A_curr = np.column_stack([A_curr, F[:, best_j]])
            coeffs_curr = best_coeffs
            pred_curr = best_pred
            bic_curr = best_bic
            selected.append(best_j)
            remaining.remove(best_j)

        # Backward elimination
        improved = True
        while improved and len(selected) > 0:
            improved = False
            best_bic = bic_curr
            best_remove_idx = None
            for idx_pos, j in enumerate(selected):
                cols = [0] + [1 + k for k in range(len(selected)) if k != idx_pos]  # 0 is intercept column
                A_try = A_curr[:, cols]
                c_try, p_try, b_try, _ = fit_and_bic(A_try, y)
                if b_try + bic_tol < best_bic:
                    best_bic = b_try
                    best_remove_idx = idx_pos
                    best_coeffs = c_try
                    best_pred = p_try
            if best_remove_idx is not None:
                # Remove that feature
                keep_mask = np.ones(A_curr.shape[1], dtype=bool)
                keep_mask[1 + best_remove_idx] = False
                A_curr = A_curr[:, keep_mask]
                removed = selected.pop(best_remove_idx)
                coeffs_curr = best_coeffs
                pred_curr = best_pred
                bic_curr = best_bic
                improved = True

        # Final refit on selected features
        if len(selected) > 0:
            A_final = np.column_stack([ones, F[:, selected]])
        else:
            A_final = ones.reshape(-1, 1)
        coeffs_final, pred_final, _, _ = fit_and_bic(A_final, y)
        intercept = coeffs_final[0]
        feature_coefs = coeffs_final[1:] if len(coeffs_final) > 1 else np.array([])

        # Map selected feature names to coefficients
        name_to_coef = {}
        for idx, coef in zip(selected, feature_coefs):
            nm = names[idx]
            name_to_coef[nm] = coef

        # Combine sin(x1) & cos(x1) into amplitude-phase if both present
        terms = []
        # Helper to add a term
        def add_term(coef, values, basis_str, meta=None):
            terms.append({"coef": coef, "values": values, "basis": basis_str, "meta": meta})

        # Intercept term
        add_term(intercept, np.ones_like(y), "1", {"type": "const"})

        # Amplitude-phase for x1
        a1 = name_to_coef.get("sin(x1)", 0.0)
        b1 = name_to_coef.get("cos(x1)", 0.0)
        used_x1_sin = "sin(x1)" in name_to_coef
        used_x1_cos = "cos(x1)" in name_to_coef

        if used_x1_sin and used_x1_cos:
            R1 = np.hypot(a1, b1)
            phi1 = np.arctan2(b1, a1)
            phi1_s = self._float_from_formatted(phi1)
            v1 = np.sin(x1 + phi1_s)
            basis1 = f"sin(x1 + {self._format_number(abs(phi1_s))})" if phi1_s >= 0 else f"sin(x1 - {self._format_number(abs(phi1_s))})"
            add_term(R1, v1, basis1, {"type": "phase", "var": "x1"})
        else:
            if used_x1_sin:
                add_term(a1, s1, "sin(x1)", {"type": "sin", "args": ("x1",)})
            if used_x1_cos:
                add_term(b1, c1, "cos(x1)", {"type": "cos", "args": ("x1",)})

        # Amplitude-phase for x2
        a2 = name_to_coef.get("sin(x2)", 0.0)
        b2 = name_to_coef.get("cos(x2)", 0.0)
        used_x2_sin = "sin(x2)" in name_to_coef
        used_x2_cos = "cos(x2)" in name_to_coef

        if used_x2_sin and used_x2_cos:
            R2 = np.hypot(a2, b2)
            phi2 = np.arctan2(b2, a2)
            phi2_s = self._float_from_formatted(phi2)
            v2 = np.sin(x2 + phi2_s)
            basis2 = f"sin(x2 + {self._format_number(abs(phi2_s))})" if phi2_s >= 0 else f"sin(x2 - {self._format_number(abs(phi2_s))})"
            add_term(R2, v2, basis2, {"type": "phase", "var": "x2"})
        else:
            if used_x2_sin:
                add_term(a2, s2, "sin(x2)", {"type": "sin", "args": ("x2",)})
            if used_x2_cos:
                add_term(b2, c2, "cos(x2)", {"type": "cos", "args": ("x2",)})

        # Add remaining selected features (excluding ones folded)
        excluded = {"sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)"} if (used_x1_sin and used_x1_cos) or (used_x2_sin and used_x2_cos) else set()
        for nm, coef in name_to_coef.items():
            if nm in excluded:
                continue
            if nm in {"sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)"}:
                # Already added above
                continue
            # Find its values
            idx = names.index(nm)
            vals = F[:, idx]
            add_term(coef, vals, nm, feats[idx][2])

        # Round coefficients to stabilize expression; use formatted numbers for final predictions
        for t in terms:
            t["coef"] = self._float_from_formatted(t["coef"])

        # Build predictions consistent with rounded coefficients and rounded phase angles used
        yhat = np.zeros_like(y)
        for t in terms:
            yhat += t["coef"] * t["values"]

        # Build expression string
        # Prefer ordering: const, x1/x2 phase terms, simple univariate, sum/diff trig, products, vars
        priority = {
            "const": 0,
            "phase_x1": 1,
            "phase_x2": 2,
            "sin_x1": 3,
            "cos_x1": 4,
            "sin_x2": 5,
            "cos_x2": 6,
            "sumdiff": 7,
            "prod": 8,
            "var": 9,
            "other": 10,
        }
        def term_priority(t):
            m = t.get("meta") or {}
            ttype = m.get("type", "other")
            if ttype == "const":
                return priority["const"]
            if ttype == "phase":
                return priority["phase_x1"] if m.get("var") == "x1" else priority["phase_x2"]
            if ttype == "sin" and m.get("args") == ("x1",):
                return priority["sin_x1"]
            if ttype == "cos" and m.get("args") == ("x1",):
                return priority["cos_x1"]
            if ttype == "sin" and m.get("args") == ("x2",):
                return priority["sin_x2"]
            if ttype == "cos" and m.get("args") == ("x2",):
                return priority["cos_x2"]
            if ttype in {"sin", "cos"} and len(m.get("args", ())) == 3:
                return priority["sumdiff"]
            if ttype == "prod":
                return priority["prod"]
            if ttype == "var":
                return priority["var"]
            return priority["other"]

        terms_sorted = sorted(terms, key=term_priority)

        def format_term(coef, basis):
            # coef already rounded
            if basis == "1":
                return self._format_number(coef)
            abscoef = abs(coef)
            if abs(abscoef - 1.0) < 1e-12:
                t = basis
            else:
                t = f"{self._format_number(abscoef)}*{basis}"
            if coef < 0:
                # handle sign
                if t.startswith("-"):
                    return t
                else:
                    return f"-{t}"
            else:
                return t

        expr_parts = []
        for i, t in enumerate(terms_sorted):
            part = format_term(t["coef"], t["basis"])
            if i == 0:
                # first term: ensure no leading '+'
                if part.startswith("+"):
                    part = part[1:]
                expr_parts.append(part)
            else:
                if part.startswith("-"):
                    expr_parts.append(f" {part}")
                else:
                    expr_parts.append(f" + {part}")
        expression = "".join(expr_parts) if expr_parts else "0"

        # Compute complexity (approximate)
        # Count unary ops (sin, cos), binary ops (+, -, *, /) approximate
        unary_ops = 0
        binary_ops = 0
        # number of additions between top-level terms
        if len(terms_sorted) > 1:
            binary_ops += (len(terms_sorted) - 1)
        for t in terms_sorted:
            basis = t["basis"]
            coef = t["coef"]
            meta = t.get("meta") or {}
            if basis == "1":
                continue
            # unary function count
            if basis.startswith("sin("):
                unary_ops += 1
            elif basis.startswith("cos("):
                unary_ops += 1
            # binary inside basis
            if " + " in basis or " - " in basis:
                binary_ops += 1
            if "*" in basis:
                binary_ops += 1  # product of two trig functions

            # external multiply by coefficient (if not 1)
            if abs(abs(coef) - 1.0) >= 1e-12:
                binary_ops += 1

        complexity = 2 * binary_ops + unary_ops

        return {
            "expression": expression,
            "predictions": yhat.tolist(),
            "details": {"complexity": int(complexity)}
        }
