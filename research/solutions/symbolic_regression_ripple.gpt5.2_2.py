import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).ravel()
        n = X.shape[0]
        if n == 0:
            return {"expression": "0", "predictions": [], "details": {}}
        x1 = X[:, 0]
        x2 = X[:, 1]

        def linear_baseline():
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            try:
                coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            except Exception:
                coef = np.zeros(3, dtype=np.float64)
            pred = A @ coef
            mse = float(np.mean((pred - y) ** 2))
            a, b, c = coef
            expr = f"({a:.12g})*x1 + ({b:.12g})*x2 + ({c:.12g})"
            return mse, expr, pred

        base_mse, base_expr, base_pred = linear_baseline()

        def estimate_w0(t, yv):
            t = np.asarray(t, dtype=np.float64)
            yv = np.asarray(yv, dtype=np.float64)
            tmin = float(np.min(t))
            tmax = float(np.max(t))
            tr = tmax - tmin
            if not np.isfinite(tr) or tr <= 1e-12:
                return 1.0
            idx = np.argsort(t, kind="mergesort")
            ts = t[idx]
            ys = yv[idx]
            ngrid = 1024
            if n < 256:
                ngrid = 256
            tgrid = np.linspace(tmin, tmax, ngrid, dtype=np.float64)
            ygrid = np.interp(tgrid, ts, ys).astype(np.float64)
            try:
                p = np.polyfit(tgrid, ygrid, deg=2)
                trend = (p[0] * tgrid + p[1]) * tgrid + p[2]
                ydt = ygrid - trend
            except Exception:
                ydt = ygrid - np.mean(ygrid)
            window = np.hanning(ngrid).astype(np.float64)
            ydt = ydt * window
            fft = np.fft.rfft(ydt)
            mag = np.abs(fft)
            if mag.shape[0] <= 2:
                return 1.0
            mag[0] = 0.0
            dt = float(tgrid[1] - tgrid[0])
            if not np.isfinite(dt) or dt <= 0:
                return 1.0
            freqs = np.fft.rfftfreq(ngrid, d=dt)
            k = int(np.argmax(mag))
            f0 = float(freqs[k]) if k < freqs.shape[0] else 0.0
            w0 = 2.0 * np.pi * f0
            if not np.isfinite(w0) or w0 <= 0:
                return 1.0
            return w0

        def make_candidates(w0, t_range):
            w_min = 0.05
            w_max = 200.0
            if np.isfinite(t_range) and t_range > 1e-12:
                w_max = min(w_max, max(2.0, float(40.0 * np.pi / t_range)))
            ws = []
            ws.append(np.linspace(w_min, w_max, 50, dtype=np.float64))
            if np.isfinite(w0) and w0 > w_min and w0 < w_max:
                lo = max(w_min, w0 * 0.7)
                hi = min(w_max, w0 * 1.3)
                if hi > lo * (1.0 + 1e-12):
                    ws.append(np.linspace(lo, hi, 30, dtype=np.float64))
                ws.append(np.array([w0], dtype=np.float64))
            ws = np.unique(np.concatenate(ws))
            ws = ws[np.isfinite(ws)]
            ws = ws[(ws >= w_min) & (ws <= w_max)]
            if ws.size == 0:
                ws = np.linspace(w_min, w_max, 40, dtype=np.float64)
            return ws

        def solve_ls(A, yv):
            ATA = A.T @ A
            ATy = A.T @ yv
            tr = float(np.trace(ATA))
            ridge = 1e-12 * (tr / ATA.shape[0] if tr > 0 else 1.0)
            ATA = ATA.copy()
            ATA.flat[:: ATA.shape[0] + 1] += ridge
            try:
                coef = np.linalg.solve(ATA, ATy)
            except np.linalg.LinAlgError:
                coef, _, _, _ = np.linalg.lstsq(A, yv, rcond=None)
            return coef

        def eval_model(t, yv, deg, w, t_pows=None):
            t = np.asarray(t, dtype=np.float64)
            yv = np.asarray(yv, dtype=np.float64)
            if t_pows is None:
                t_pows = np.empty((deg + 1, t.shape[0]), dtype=np.float64)
                t_pows[0] = 1.0
                for k in range(1, deg + 1):
                    t_pows[k] = t_pows[k - 1] * t
            wt = w * t
            s = np.sin(wt)
            c = np.cos(wt)
            m = 3 * (deg + 1)
            A = np.empty((t.shape[0], m), dtype=np.float64)
            col = 0
            for k in range(deg + 1):
                A[:, col] = t_pows[k] * s
                col += 1
            for k in range(deg + 1):
                A[:, col] = t_pows[k] * c
                col += 1
            for k in range(deg + 1):
                A[:, col] = t_pows[k]
                col += 1
            coef = solve_ls(A, yv)
            pred = A @ coef
            mse = float(np.mean((pred - yv) ** 2))
            return mse, coef, pred, t_pows

        def golden_refine(t, yv, deg, w_init, w_lo, w_hi, t_pows):
            phi = (1.0 + 5.0 ** 0.5) / 2.0
            invphi = 1.0 / phi
            invphi2 = invphi * invphi
            a = float(w_lo)
            b = float(w_hi)
            if not (np.isfinite(a) and np.isfinite(b) and b > a * (1.0 + 1e-12)):
                return float(w_init), None, None, None

            cache = {}

            def f(w):
                key = float(w)
                if key in cache:
                    return cache[key]
                mse, coef, pred, _ = eval_model(t, yv, deg, key, t_pows=t_pows)
                cache[key] = (mse, coef, pred)
                return cache[key]

            c = b - (b - a) * invphi
            d = a + (b - a) * invphi
            fc = f(c)
            fd = f(d)
            for _ in range(22):
                if fc[0] < fd[0]:
                    b = d
                    d = c
                    fd = fc
                    c = b - (b - a) * invphi
                    fc = f(c)
                else:
                    a = c
                    c = d
                    fc = fd
                    d = a + (b - a) * invphi
                    fd = f(d)
                if (b - a) <= 1e-6 * (1.0 + abs(w_init)):
                    break
            best = fc if fc[0] < fd[0] else fd
            w_best = c if fc[0] < fd[0] else d
            return float(w_best), best[1], best[2], float(best[0])

        def horner(coeffs, t):
            deg = len(coeffs) - 1
            v = np.full_like(t, float(coeffs[deg]), dtype=np.float64)
            for k in range(deg - 1, -1, -1):
                v = v * t + float(coeffs[k])
            return v

        def fmt_num(v):
            if not np.isfinite(v):
                return "0"
            s = f"{float(v):.12g}"
            if s == "-0":
                s = "0"
            return s

        def build_poly_string(coeffs, var, thr):
            terms = []
            binops = 0
            for p, c in enumerate(coeffs):
                c = float(c)
                if not np.isfinite(c) or abs(c) <= thr:
                    continue
                sign = -1 if c < 0 else 1
                mag = abs(c)
                mag_str = fmt_num(mag)
                if p == 0:
                    expr = mag_str
                    ops = 0
                elif p == 1:
                    expr = f"{mag_str}*{var}"
                    ops = 1
                else:
                    expr = f"{mag_str}*{var}**{p}"
                    ops = 2
                terms.append((sign, expr, ops))
                binops += ops
            if not terms:
                return "0", 0
            poly = ""
            for i, (sign, expr, _) in enumerate(terms):
                if i == 0:
                    poly = f"-{expr}" if sign < 0 else expr
                else:
                    poly += f" - {expr}" if sign < 0 else f" + {expr}"
            binops += (len(terms) - 1)
            return poly, binops

        def build_expression(t_kind, deg, w, coef, y_scale):
            if t_kind == "r2":
                t_expr = "(x1**2 + x2**2)"
                t_opcount = 3
            else:
                t_expr = "(x1**2 + x2**2)**0.5"
                t_opcount = 4

            d = deg
            p = np.array(coef[0 : d + 1], dtype=np.float64)
            q = np.array(coef[d + 1 : 2 * (d + 1)], dtype=np.float64)
            r = np.array(coef[2 * (d + 1) : 3 * (d + 1)], dtype=np.float64)

            maxabs = float(np.max(np.abs(coef[np.isfinite(coef)]))) if np.any(np.isfinite(coef)) else 0.0
            thr = max(1e-10, 1e-6 * max(1.0, y_scale, maxabs))

            p[np.abs(p) <= thr] = 0.0
            q[np.abs(q) <= thr] = 0.0
            r[np.abs(r) <= thr] = 0.0

            p_str, p_bin = build_poly_string(p, t_expr, thr)
            q_str, q_bin = build_poly_string(q, t_expr, thr)
            r_str, r_bin = build_poly_string(r, t_expr, thr)
            w_str = fmt_num(w)

            parts = []
            binops = 0
            unaryops = 0

            if p_str != "0":
                parts.append(f"({p_str})*sin(({w_str})*{t_expr})")
                binops += p_bin + 2 + t_opcount  # P ops + (w*t) '*' + P*sin '*', plus t_expr ops once for this occurrence
                unaryops += 1
            if q_str != "0":
                parts.append(f"({q_str})*cos(({w_str})*{t_expr})")
                binops += q_bin + 2 + t_opcount
                unaryops += 1
            if r_str != "0":
                parts.append(f"({r_str})")
                binops += r_bin

            if not parts:
                expr = "0"
                C = 0
            else:
                expr = " + ".join(parts)
                binops += (len(parts) - 1)
                C = int(2 * binops + unaryops)

            return expr, p, q, r, C

        def fit_family(t_kind, deg):
            if t_kind == "r2":
                t = (x1 * x1 + x2 * x2).astype(np.float64)
            else:
                t = np.sqrt((x1 * x1 + x2 * x2).astype(np.float64) + 0.0)

            tmin = float(np.min(t))
            tmax = float(np.max(t))
            t_range = tmax - tmin
            w0 = estimate_w0(t, y)
            ws = make_candidates(w0, t_range)
            t_pows = np.empty((deg + 1, n), dtype=np.float64)
            t_pows[0] = 1.0
            for k in range(1, deg + 1):
                t_pows[k] = t_pows[k - 1] * t

            best = (np.inf, None, None, None)  # mse, w, coef, pred
            for w in ws:
                mse, coef, pred, _ = eval_model(t, y, deg, float(w), t_pows=t_pows)
                if mse < best[0]:
                    best = (mse, float(w), coef, pred)

            w_init = best[1] if best[1] is not None else float(w0 if np.isfinite(w0) else 1.0)
            w_lo = max(0.05, w_init * 0.85)
            w_hi = min(200.0, w_init * 1.15)
            w_ref, coef_ref, pred_ref, mse_ref = golden_refine(t, y, deg, w_init, w_lo, w_hi, t_pows)
            if mse_ref is not None and mse_ref < best[0]:
                best = (mse_ref, w_ref, coef_ref, pred_ref)

            return {
                "mse": float(best[0]),
                "w": float(best[1]),
                "coef": np.asarray(best[2], dtype=np.float64),
                "pred": np.asarray(best[3], dtype=np.float64),
                "t_kind": t_kind,
                "deg": deg,
                "t": t,
            }

        y_scale = float(np.std(y)) if np.isfinite(np.std(y)) and np.std(y) > 0 else float(np.max(np.abs(y)) + 1e-12)

        candidates = []
        for t_kind in ("r2", "r"):
            for deg in (1, 2):
                try:
                    candidates.append(fit_family(t_kind, deg))
                except Exception:
                    continue

        if not candidates:
            return {"expression": base_expr, "predictions": base_pred.tolist(), "details": {"complexity": 0}}

        # Choose best by MSE; break near-ties by lower estimated complexity
        best_expr = None
        best_pred = None
        best_mse = np.inf
        best_C = None

        for cand in candidates:
            expr, p, q, r, C = build_expression(cand["t_kind"], cand["deg"], cand["w"], cand["coef"], y_scale)

            # Recompute predictions from pruned coefficients (so they match expression)
            t = cand["t"]
            w = cand["w"]
            wt = w * t
            s = np.sin(wt)
            c = np.cos(wt)
            pv = horner(p, t)
            qv = horner(q, t)
            rv = horner(r, t)
            pred = pv * s + qv * c + rv
            mse = float(np.mean((pred - y) ** 2))

            if mse < best_mse * (1.0 - 1e-12):
                best_mse = mse
                best_expr = expr
                best_pred = pred
                best_C = C
            else:
                # If very close, choose simpler
                if best_mse < np.inf and mse <= best_mse * 1.005 and (best_C is None or C < best_C):
                    best_mse = mse
                    best_expr = expr
                    best_pred = pred
                    best_C = C

        # If somehow worse than linear, return linear
        if not np.isfinite(best_mse) or best_mse > base_mse:
            return {"expression": base_expr, "predictions": base_pred.tolist(), "details": {"complexity": 0}}

        return {
            "expression": best_expr,
            "predictions": best_pred.tolist(),
            "details": {"complexity": int(best_C) if best_C is not None else 0},
        }