import numpy as np

def _exp_clip(z):
    return np.exp(np.clip(z, -60.0, 60.0))

def _generate_exponents_4vars(max_degree):
    exps = []
    for total in range(max_degree + 1):
        for e1 in range(total + 1):
            rem1 = total - e1
            for e2 in range(rem1 + 1):
                rem2 = rem1 - e2
                for e3 in range(rem2 + 1):
                    e4 = rem2 - e3
                    exps.append((e1, e2, e3, e4))
    return exps

def _generate_exponents_2vars(max_degree):
    exps = []
    for total in range(max_degree + 1):
        for e1 in range(total + 1):
            e2 = total - e1
            exps.append((e1, e2))
    return exps

def _monomial_expr_4(e):
    e1, e2, e3, e4 = e
    parts = []
    if e1:
        parts.append("x1" if e1 == 1 else f"x1**{e1}")
    if e2:
        parts.append("x2" if e2 == 1 else f"x2**{e2}")
    if e3:
        parts.append("x3" if e3 == 1 else f"x3**{e3}")
    if e4:
        parts.append("x4" if e4 == 1 else f"x4**{e4}")
    return "1" if not parts else "*".join(parts)

def _monomial_expr_2(e):
    e1, e2 = e
    parts = []
    if e1:
        parts.append("x1" if e1 == 1 else f"x1**{e1}")
    if e2:
        parts.append("x2" if e2 == 1 else f"x2**{e2}")
    return "1" if not parts else "*".join(parts)

def _eval_monomial_4(x1, x2, x3, x4, e):
    e1, e2, e3, e4 = e
    out = np.ones_like(x1, dtype=np.float64)
    if e1:
        out *= x1 ** e1
    if e2:
        out *= x2 ** e2
    if e3:
        out *= x3 ** e3
    if e4:
        out *= x4 ** e4
    return out

def _eval_monomial_2(x1, x2, e):
    e1, e2 = e
    out = np.ones_like(x1, dtype=np.float64)
    if e1:
        out *= x1 ** e1
    if e2:
        out *= x2 ** e2
    return out

def _ridge_solve(A, y, alpha):
    # Solve (A^T A + alpha I) w = A^T y
    ATA = A.T @ A
    ATy = A.T @ y
    if alpha > 0.0:
        ATA = ATA + alpha * np.eye(ATA.shape[0], dtype=ATA.dtype)
    try:
        return np.linalg.solve(ATA, ATy)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(A, y, rcond=None)[0]

def _stlsq(A, y, alpha, tol, max_iter=12):
    m = A.shape[1]
    active = np.ones(m, dtype=bool)
    w = np.zeros(m, dtype=np.float64)
    last_active = None
    for _ in range(max_iter):
        idx = np.flatnonzero(active)
        if idx.size == 0:
            return w, active
        Aw = A[:, idx]
        w_sub = _ridge_solve(Aw, y, alpha)
        w[:] = 0.0
        w[idx] = w_sub
        if tol > 0.0:
            active_new = np.abs(w) >= tol
        else:
            active_new = active.copy()
        if last_active is not None and np.array_equal(active_new, last_active):
            active = active_new
            break
        if np.array_equal(active_new, active):
            break
        last_active = active.copy()
        active = active_new
    return w, active

def _build_feature_library(X):
    x1 = X[:, 0].astype(np.float64, copy=False)
    x2 = X[:, 1].astype(np.float64, copy=False)
    x3 = X[:, 2].astype(np.float64, copy=False)
    x4 = X[:, 3].astype(np.float64, copy=False)

    exps_all_deg3 = _generate_exponents_4vars(3)
    exps_x1x2_deg3 = _generate_exponents_2vars(3)
    exps_lin_all = [(0, 0, 0, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]

    kset = (0.5, 1.0, 2.0)

    dampers = []

    # x3,x4-based dampers
    s34 = x3 * x3 + x4 * x4
    sp = (x3 + x4) * (x3 + x4)
    sm = (x3 - x4) * (x3 - x4)
    p = (x3 * x4) * (x3 * x4)

    for k in kset:
        dampers.append((_exp_clip(-k * s34), f"exp(-({k}*(x3**2 + x4**2)))"))
    for k in kset:
        dampers.append((_exp_clip(-k * sp), f"exp(-({k}*((x3 + x4)**2)))"))
    for k in kset:
        dampers.append((_exp_clip(-k * sm), f"exp(-({k}*((x3 - x4)**2)))"))
    for k in kset:
        dampers.append((_exp_clip(-k * p), f"exp(-({k}*((x3*x4)**2)))"))

    # x1,x2 Gaussian-like dampers
    s12 = x1 * x1 + x2 * x2
    for k in kset:
        dampers.append((_exp_clip(-k * s12), f"exp(-({k}*(x1**2 + x2**2)))"))

    # full Gaussian-like dampers
    sall = s12 + s34
    for k in kset:
        dampers.append((_exp_clip(-k * sall), f"exp(-({k}*(x1**2 + x2**2 + x3**2 + x4**2)))"))

    features = []
    exprs = []

    # Base polynomial terms (deg <= 3 in all vars)
    for e in exps_all_deg3:
        v = _eval_monomial_4(x1, x2, x3, x4, e)
        features.append(v)
        exprs.append(_monomial_expr_4(e))

    # Damped terms: polynomial in x1,x2 (deg <= 3) times each damper
    for dval, dexpr in dampers:
        for e in exps_x1x2_deg3:
            mval = _eval_monomial_2(x1, x2, e)
            v = dval * mval
            mex = _monomial_expr_2(e)
            if mex == "1":
                fexpr = dexpr
            else:
                fexpr = f"({mex})*({dexpr})"
            features.append(v)
            exprs.append(fexpr)

    # Damped linear terms in all vars times each damper (captures x3/x4 modulation etc.)
    for dval, dexpr in dampers:
        for e in exps_lin_all:
            mval = _eval_monomial_4(x1, x2, x3, x4, e)
            mex = _monomial_expr_4(e)
            if mex == "1":
                fexpr = dexpr
                v = dval
            else:
                fexpr = f"({mex})*({dexpr})"
                v = mval * dval
            features.append(v)
            exprs.append(fexpr)

    Theta = np.column_stack(features).astype(np.float64, copy=False)
    return Theta, exprs

def _format_float(c):
    if not np.isfinite(c):
        c = 0.0
    if abs(c) < 1e-16:
        c = 0.0
    s = f"{c:.15g}"
    if s == "-0":
        s = "0"
    return s

def _build_expression(exprs, coefs, min_abs_coef=0.0):
    terms = []
    for e, c in zip(exprs, coefs):
        if not np.isfinite(c):
            continue
        if abs(c) <= min_abs_coef:
            continue
        if e == "1":
            terms.append((_format_float(c), None))
        else:
            terms.append((_format_float(c), e))

    if not terms:
        return "0"

    # Put constant first if exists, then others by descending abs coef.
    const_terms = [(c, e) for c, e in terms if e is None]
    other_terms = [(c, e) for c, e in terms if e is not None]
    other_terms.sort(key=lambda t: abs(float(t[0])) if t[0] not in ("nan", "inf", "-inf") else 0.0, reverse=True)

    ordered = const_terms + other_terms
    out = []
    for i, (c_str, e) in enumerate(ordered):
        c_val = float(c_str)
        if e is None:
            term = c_str
        else:
            if c_val == 1.0:
                term = f"({e})"
            elif c_val == -1.0:
                term = f"-({e})"
            else:
                term = f"{c_str}*({e})"

        if i == 0:
            out.append(term)
        else:
            if term.startswith("-"):
                out.append(term)
            else:
                out.append(f"+{term}")
    return "".join(out)

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 0))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y, dtype=np.float64)

        n, d = X.shape
        if d != 4 or n == 0:
            return {"expression": "0", "predictions": [0.0] * int(n), "details": {"complexity": 0}}

        Theta, exprs = _build_feature_library(X)

        # Remove any columns with NaNs/Infs
        finite_cols = np.isfinite(Theta).all(axis=0)
        Theta = Theta[:, finite_cols]
        exprs = [e for e, ok in zip(exprs, finite_cols) if ok]

        # Scale columns by L2 norm for conditioning (no centering)
        col_norms = np.linalg.norm(Theta, axis=0)
        col_norms = np.where(col_norms > 0.0, col_norms, 1.0)
        Theta_s = Theta / col_norms

        # Train/validation split
        rng = np.random.default_rng(self.random_state)
        idx = rng.permutation(n)
        n_val = int(0.2 * n)
        if n >= 250:
            n_val = max(n_val, 50)
        n_val = max(1, min(n - 1, n_val))
        val_idx = idx[:n_val]
        tr_idx = idx[n_val:]

        A_tr = Theta_s[tr_idx]
        y_tr = y[tr_idx]
        A_val = Theta_s[val_idx]
        y_val = y[val_idx]

        # Initial fit to set tolerance scale
        alpha0 = 1e-10
        w0 = _ridge_solve(A_tr, y_tr, alpha0)
        coefs0 = w0 / col_norms
        max_coef = float(np.max(np.abs(coefs0))) if coefs0.size else 1.0
        if not np.isfinite(max_coef) or max_coef <= 0.0:
            max_coef = 1.0

        tols = [0.0]
        for t in (max_coef * np.logspace(-8, -2, 10)).tolist():
            if t > 0:
                tols.append(float(t))
        # Add a slightly stronger pruning level
        tols.append(max_coef * 5e-2)

        alphas = [0.0, 1e-12, 1e-10, 1e-8, 1e-6]

        best = None
        best_mse = None
        best_terms = None
        best_alpha = None
        best_tol = None
        best_active = None

        y_var = float(np.var(y_tr)) + 1e-12

        for alpha in alphas:
            for tol in tols:
                w_s, active = _stlsq(A_tr, y_tr, alpha=alpha, tol=tol, max_iter=12)
                if not np.any(active):
                    continue
                pred_val = A_val @ w_s
                err = y_val - pred_val
                mse = float(np.mean(err * err))
                terms = int(np.count_nonzero(active))

                # Slight penalty for large models
                penalty = (1.0 + 0.0025 * max(0, terms - 12))
                score = mse * penalty + 1e-10 * terms * y_var

                if best is None or score < best:
                    best = score
                    best_mse = mse
                    best_terms = terms
                    best_alpha = alpha
                    best_tol = tol
                    best_active = active.copy()

        if best_active is None or not np.any(best_active):
            # Fall back to linear regression on x1..x4 + bias
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
            A = np.column_stack([x1, x2, x3, x4, np.ones(n, dtype=np.float64)])
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c, d, e = coef.tolist()
            expr = f"{_format_float(a)}*x1+{_format_float(b)}*x2+{_format_float(c)}*x3+{_format_float(d)}*x4+{_format_float(e)}"
            pred = (A @ coef).astype(np.float64, copy=False)
            return {"expression": expr, "predictions": pred.tolist(), "details": {"complexity": 5}}

        # Refit on full data with selected active set
        A_full = Theta_s[:, best_active]
        w_full = _ridge_solve(A_full, y, best_alpha)
        w_s_full = np.zeros(Theta_s.shape[1], dtype=np.float64)
        w_s_full[np.flatnonzero(best_active)] = w_full

        coefs = w_s_full / col_norms
        # Drop ultra-small coefficients
        min_abs = float(np.max(np.abs(coefs)) * 1e-10) if coefs.size else 0.0
        expression = _build_expression(exprs, coefs, min_abs_coef=min_abs)

        # Predictions using our fitted linear combination
        predictions = (Theta @ coefs).astype(np.float64, copy=False)

        used_terms = int(np.sum(np.abs(coefs) > min_abs))

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {
                "complexity": used_terms,
                "val_mse": best_mse,
                "terms": best_terms,
                "alpha": best_alpha,
                "tol": best_tol,
            },
        }