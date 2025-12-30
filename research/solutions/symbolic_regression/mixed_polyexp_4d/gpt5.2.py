import numpy as np

def _format_float(x: float) -> str:
    if not np.isfinite(x):
        return "0.0"
    s = f"{x:.12g}"
    if s == "-0":
        s = "0"
    return s

def _monomial_str(exps):
    e1, e2, e3, e4 = exps
    parts = []
    if e1:
        parts.append("x1" if e1 == 1 else f"x1**{e1}")
    if e2:
        parts.append("x2" if e2 == 1 else f"x2**{e2}")
    if e3:
        parts.append("x3" if e3 == 1 else f"x3**{e3}")
    if e4:
        parts.append("x4" if e4 == 1 else f"x4**{e4}")
    if not parts:
        return "1"
    return "*".join(parts)

def _format_sum(terms, coef_eps=1e-14):
    kept = [(c, f) for (c, f) in terms if np.isfinite(c) and abs(c) > coef_eps]
    if not kept:
        return "0.0"

    def pos_term_str(cpos, factor):
        if factor == "1":
            return _format_float(cpos)
        if abs(cpos - 1.0) <= 1e-14:
            return factor
        return f"{_format_float(cpos)}*{factor}"

    c0, f0 = kept[0]
    if c0 >= 0:
        out = pos_term_str(c0, f0)
    else:
        out = "-" + pos_term_str(-c0, f0)

    for c, f in kept[1:]:
        if c >= 0:
            out += " + " + pos_term_str(c, f)
        else:
            out += " - " + pos_term_str(-c, f)
    return out

def _ridge_fit(A, y, alpha=0.0, reg_mask=None):
    # Solve (A^T A + alpha*I_reg) w = A^T y
    AT = A.T
    ATA = AT @ A
    ATy = AT @ y
    if alpha > 0.0:
        if reg_mask is None:
            reg_mask = np.ones(ATA.shape[0], dtype=bool)
        idx = np.where(reg_mask)[0]
        ATA[idx, idx] += alpha
    try:
        w = np.linalg.solve(ATA, ATy)
    except np.linalg.LinAlgError:
        w = np.linalg.lstsq(A, y, rcond=None)[0]
    return w

def _generate_exponents_upto(max_deg):
    exps = []
    for e1 in range(max_deg + 1):
        for e2 in range(max_deg - e1 + 1):
            for e3 in range(max_deg - e1 - e2 + 1):
                for e4 in range(max_deg - e1 - e2 - e3 + 1):
                    exps.append((e1, e2, e3, e4))
    return exps

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        if X.ndim != 2 or X.shape[1] != 4 or y.shape[0] != n or n == 0:
            expr = "0.0"
            return {"expression": expr, "predictions": [0.0] * int(n), "details": {}}

        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        # Linear baseline
        A_lin = np.column_stack([x1, x2, x3, x4, np.ones(n, dtype=np.float64)])
        w_lin = np.linalg.lstsq(A_lin, y, rcond=None)[0]
        pred_lin = A_lin @ w_lin
        mse_lin = float(np.mean((y - pred_lin) ** 2))

        # Build candidate basis: monomials and monomials * exp(-b * sum_{i in subset} xi^2)
        max_pow = 4
        x1p = [np.ones(n, dtype=np.float64)]
        x2p = [np.ones(n, dtype=np.float64)]
        x3p = [np.ones(n, dtype=np.float64)]
        x4p = [np.ones(n, dtype=np.float64)]
        for k in range(1, max_pow + 1):
            x1p.append(x1p[-1] * x1)
            x2p.append(x2p[-1] * x2)
            x3p.append(x3p[-1] * x3)
            x4p.append(x4p[-1] * x4)

        x_sq = [x1p[2], x2p[2], x3p[2], x4p[2]]

        damping_entries = []

        # Non-damped (None)
        damping_entries.append({
            "expr": None,
            "arr": None,
            "subset": None,
            "b": None,
            "max_deg": 4,
            "name": "none",
        })

        # Single-variable dampings
        b_single = 1.0
        for i in range(4):
            sumsq = x_sq[i]
            expr = f"exp(-{_format_float(b_single)}*(x{i+1}**2))"
            damping_entries.append({
                "expr": expr,
                "arr": np.exp(-b_single * sumsq),
                "subset": (i,),
                "b": b_single,
                "max_deg": 2,
                "name": f"s{i+1}",
            })

        # Pairwise dampings
        b_pair = 1.0
        for i in range(4):
            for j in range(i + 1, 4):
                sumsq = x_sq[i] + x_sq[j]
                expr = f"exp(-{_format_float(b_pair)}*(x{i+1}**2 + x{j+1}**2))"
                damping_entries.append({
                    "expr": expr,
                    "arr": np.exp(-b_pair * sumsq),
                    "subset": (i, j),
                    "b": b_pair,
                    "max_deg": 2,
                    "name": f"p{i+1}{j+1}",
                })

        # Full r2 dampings with a couple of b values; allow higher-degree monomials
        for b_full in (0.5, 1.0):
            sumsq = x_sq[0] + x_sq[1] + x_sq[2] + x_sq[3]
            expr = f"exp(-{_format_float(b_full)}*(x1**2 + x2**2 + x3**2 + x4**2))"
            damping_entries.append({
                "expr": expr,
                "arr": np.exp(-b_full * sumsq),
                "subset": (0, 1, 2, 3),
                "b": b_full,
                "max_deg": 3,
                "name": f"r2_{b_full}",
            })

        exps_upto4 = _generate_exponents_upto(4)
        exps_upto3 = _generate_exponents_upto(3)
        exps_upto2 = _generate_exponents_upto(2)

        candidates = []  # (damp_idx, exps, mon_str)
        cols = []

        for damp_idx, de in enumerate(damping_entries):
            max_deg = de["max_deg"]
            if damp_idx == 0:
                exps_list = exps_upto4
                # exclude constant for non-damped; intercept handled separately
                for exps in exps_list:
                    if sum(exps) == 0 or sum(exps) > max_deg:
                        continue
                    e1, e2, e3, e4 = exps
                    col = x1p[e1] * x2p[e2] * x3p[e3] * x4p[e4]
                    cols.append(col)
                    candidates.append((damp_idx, exps, _monomial_str(exps)))
            else:
                if max_deg == 2:
                    exps_list = exps_upto2
                elif max_deg == 3:
                    exps_list = exps_upto3
                else:
                    exps_list = _generate_exponents_upto(max_deg)
                damp_arr = de["arr"]
                for exps in exps_list:
                    if sum(exps) > max_deg:
                        continue
                    e1, e2, e3, e4 = exps
                    col = (x1p[e1] * x2p[e2] * x3p[e3] * x4p[e4]) * damp_arr
                    cols.append(col)
                    candidates.append((damp_idx, exps, _monomial_str(exps)))

        if not cols:
            expr = "0.0"
            return {"expression": expr, "predictions": [0.0] * int(n), "details": {}}

        Phi = np.column_stack(cols).astype(np.float64, copy=False)  # (n, m)
        m = Phi.shape[1]

        sum_phi = Phi.sum(axis=0)
        sum_phi2 = (Phi * Phi).sum(axis=0)
        mean_phi = sum_phi / float(n)
        centered_ss = sum_phi2 - float(n) * mean_phi * mean_phi
        centered_ss = np.maximum(centered_ss, 1e-30)
        centered_norm = np.sqrt(centered_ss)

        # OMP-like selection
        max_terms = int(self.kwargs.get("max_terms", 14))
        max_terms = max(1, min(max_terms, 25))

        y_mean = float(np.mean(y))
        residual = y - y_mean
        selected = []
        selected_mask = np.zeros(m, dtype=bool)

        best_mse = float(np.mean(residual ** 2))
        prev_mse = best_mse

        for _ in range(max_terms):
            res_sum = float(np.sum(residual))
            dot = Phi.T @ residual  # (m,)
            dot_center = dot - mean_phi * res_sum
            corr = np.abs(dot_center) / centered_norm
            corr[selected_mask] = -np.inf
            j = int(np.argmax(corr))
            if not np.isfinite(corr[j]) or corr[j] <= 1e-12:
                break

            selected.append(j)
            selected_mask[j] = True

            A = np.column_stack([np.ones(n, dtype=np.float64), Phi[:, selected]])
            alpha = float(self.kwargs.get("ridge_alpha", 0.0))
            if alpha <= 0.0:
                alpha = 1e-10 * float(np.var(y) + 1e-12)
            reg_mask = np.ones(A.shape[1], dtype=bool)
            reg_mask[0] = False
            w = _ridge_fit(A, y, alpha=alpha, reg_mask=reg_mask)
            pred = A @ w
            residual = y - pred
            mse = float(np.mean(residual ** 2))

            if mse < best_mse:
                best_mse = mse

            # stop if improvement is negligible
            if prev_mse - mse < 1e-12 * (1.0 + prev_mse):
                if len(selected) >= 6:
                    break
            prev_mse = mse

        if not selected:
            # fallback to linear
            a, b, c, d, e = w_lin
            expr = f"{_format_float(a)}*x1 + {_format_float(b)}*x2 + {_format_float(c)}*x3 + {_format_float(d)}*x4 + {_format_float(e)}"
            return {"expression": expr, "predictions": pred_lin.tolist(), "details": {}}

        # Final fit with selected
        A = np.column_stack([np.ones(n, dtype=np.float64), Phi[:, selected]])
        alpha = float(self.kwargs.get("ridge_alpha", 0.0))
        if alpha <= 0.0:
            alpha = 1e-10 * float(np.var(y) + 1e-12)
        reg_mask = np.ones(A.shape[1], dtype=bool)
        reg_mask[0] = False
        w = _ridge_fit(A, y, alpha=alpha, reg_mask=reg_mask)
        pred = A @ w
        mse = float(np.mean((y - pred) ** 2))

        if not np.isfinite(mse) or mse >= mse_lin * 0.999999:
            a, b, c, d, e = w_lin
            expr = f"{_format_float(a)}*x1 + {_format_float(b)}*x2 + {_format_float(c)}*x3 + {_format_float(d)}*x4 + {_format_float(e)}"
            return {"expression": expr, "predictions": pred_lin.tolist(), "details": {}}

        # Prune tiny coefficients
        coef = w[1:].copy()
        intercept = float(w[0])
        y_scale = float(np.std(y) + 1e-12)
        tol = 1e-10 * y_scale

        keep_sel = []
        keep_coef = []
        for idx_in_sel, j in enumerate(selected):
            cj = float(coef[idx_in_sel])
            if np.isfinite(cj) and abs(cj) > tol:
                keep_sel.append(j)
                keep_coef.append(cj)

        selected = keep_sel
        coef = np.array(keep_coef, dtype=np.float64)

        if len(selected) == 0:
            # just intercept
            expr = _format_float(intercept)
            pred2 = np.full(n, intercept, dtype=np.float64)
            if float(np.mean((y - pred2) ** 2)) >= mse_lin:
                a, b, c, d, e = w_lin
                expr = f"{_format_float(a)}*x1 + {_format_float(b)}*x2 + {_format_float(c)}*x3 + {_format_float(d)}*x4 + {_format_float(e)}"
                return {"expression": expr, "predictions": pred_lin.tolist(), "details": {}}
            return {"expression": expr, "predictions": pred2.tolist(), "details": {}}

        # Refit after pruning
        A2 = np.column_stack([np.ones(n, dtype=np.float64), Phi[:, selected]])
        reg_mask = np.ones(A2.shape[1], dtype=bool)
        reg_mask[0] = False
        w2 = _ridge_fit(A2, y, alpha=alpha, reg_mask=reg_mask)
        intercept = float(w2[0])
        coef = w2[1:].astype(np.float64, copy=False)
        pred = A2 @ w2
        mse2 = float(np.mean((y - pred) ** 2))
        if not np.isfinite(mse2) or mse2 >= mse_lin * 0.999999:
            a, b, c, d, e = w_lin
            expr = f"{_format_float(a)}*x1 + {_format_float(b)}*x2 + {_format_float(c)}*x3 + {_format_float(d)}*x4 + {_format_float(e)}"
            return {"expression": expr, "predictions": pred_lin.tolist(), "details": {}}

        # Build grouped expression
        # damping_entries[0] has expr None (no damping)
        groups = {}  # damp_idx -> list[(coeff, mon_str)]
        groups.setdefault(0, []).append((intercept, "1"))

        for c, j in zip(coef.tolist(), selected):
            damp_idx, exps, mon_str = candidates[j]
            groups.setdefault(damp_idx, []).append((float(c), mon_str))

        components = []
        for damp_idx, term_list in groups.items():
            # Combine same monomial within group
            agg = {}
            for c, mon in term_list:
                agg[mon] = agg.get(mon, 0.0) + c
            poly_terms = [(c, mon) for mon, c in agg.items()]
            poly_str = _format_sum(poly_terms, coef_eps=tol)
            if poly_str == "0.0":
                continue
            if damp_idx == 0:
                components.append(poly_str)
            else:
                damp_expr = damping_entries[damp_idx]["expr"]
                components.append(f"({poly_str})*{damp_expr}")

        if not components:
            expr = "0.0"
            return {"expression": expr, "predictions": [0.0] * int(n), "details": {}}

        expression = components[0]
        for comp in components[1:]:
            expression = f"({expression}) + ({comp})"

        return {
            "expression": expression,
            "predictions": pred.tolist(),
            "details": {}
        }