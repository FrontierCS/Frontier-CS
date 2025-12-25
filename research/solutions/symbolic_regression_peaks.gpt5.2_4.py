import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        if n == 0:
            return {"expression": "0.0", "predictions": [], "details": {}}

        x1 = X[:, 0]
        x2 = X[:, 1]

        def mse(a, b):
            r = a - b
            return float(np.mean(r * r))

        # Baseline linear regression
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        try:
            coef_lin, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            pred_lin = A @ coef_lin
            mse_lin = mse(pred_lin, y)
        except Exception:
            coef_lin = np.array([0.0, 0.0, np.mean(y)])
            pred_lin = A @ coef_lin
            mse_lin = mse(pred_lin, y)

        # Peaks-like basis (MATLAB peaks-inspired)
        e1 = np.exp(-(x1 * x1) - (x2 + 1.0) * (x2 + 1.0))
        e2 = np.exp(-(x1 * x1) - (x2 * x2))
        e3 = np.exp(-((x1 + 1.0) * (x1 + 1.0)) - (x2 * x2))

        f1 = (1.0 - x1) * (1.0 - x1) * e1
        f2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * e2
        f3 = e3

        B_peaks = np.column_stack([f1, f2, f3, np.ones_like(x1)])
        try:
            coef_peaks, _, _, _ = np.linalg.lstsq(B_peaks, y, rcond=None)
            pred_peaks = B_peaks @ coef_peaks
            mse_peaks = mse(pred_peaks, y)
        except Exception:
            coef_peaks = np.array([0.0, 0.0, 0.0, np.mean(y)])
            pred_peaks = np.full_like(y, coef_peaks[-1])
            mse_peaks = mse(pred_peaks, y)

        # Candidate library for greedy selection if needed
        def build_candidates(x1, x2):
            exp00 = np.exp(-(x1 * x1) - (x2 * x2))
            exp0p1 = np.exp(-(x1 * x1) - (x2 - 1.0) * (x2 - 1.0))
            exp0m1 = np.exp(-(x1 * x1) - (x2 + 1.0) * (x2 + 1.0))
            expp10 = np.exp(-((x1 - 1.0) * (x1 - 1.0)) - (x2 * x2))
            expm10 = np.exp(-((x1 + 1.0) * (x1 + 1.0)) - (x2 * x2))

            cand = []
            # Peaks-like primitives
            cand.append(((1.0 - x1) * (1.0 - x1) * exp0m1, "(1 - x1)**2*exp(-(x1**2) - (x2 + 1)**2)"))
            cand.append(((x1 / 5.0 - x1 ** 3 - x2 ** 5) * exp00, "(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)"))
            cand.append((expm10, "exp(-(x1 + 1)**2 - x2**2)"))

            # Simple Gaussians
            cand.append((exp00, "exp(-x1**2 - x2**2)"))
            cand.append((exp0p1, "exp(-x1**2 - (x2 - 1)**2)"))
            cand.append((exp0m1, "exp(-x1**2 - (x2 + 1)**2)"))
            cand.append((expp10, "exp(-(x1 - 1)**2 - x2**2)"))
            cand.append((expm10, "exp(-(x1 + 1)**2 - x2**2)"))

            # Polynomial-modulated Gaussians
            cand.append((x1 * exp00, "x1*exp(-x1**2 - x2**2)"))
            cand.append((x2 * exp00, "x2*exp(-x1**2 - x2**2)"))
            cand.append(((x1 * x1) * exp00, "x1**2*exp(-x1**2 - x2**2)"))
            cand.append(((x2 * x2) * exp00, "x2**2*exp(-x1**2 - x2**2)"))
            cand.append(((x1 * x2) * exp00, "(x1*x2)*exp(-x1**2 - x2**2)"))

            # Pure polynomial terms (for safety)
            cand.append((x1, "x1"))
            cand.append((x2, "x2"))
            cand.append((x1 * x1, "x1**2"))
            cand.append((x2 * x2, "x2**2"))
            cand.append((x1 ** 3, "x1**3"))
            cand.append((x2 ** 3, "x2**3"))
            cand.append((x1 * x2, "x1*x2"))
            cand.append((x2 ** 5, "x2**5"))

            return cand

        candidates = build_candidates(x1, x2)

        def greedy_fit(candidates, y, max_terms=5):
            y = y.reshape(-1)
            ones = np.ones_like(y)
            selected = []
            remaining = list(range(len(candidates)))
            best = None  # (mse, selected, coef, pred)
            resid = y.copy()

            for step in range(max_terms):
                # pick best correlated term with residual
                best_i = None
                best_score = -1.0
                for idx in remaining:
                    t = candidates[idx][0]
                    if t.shape[0] != y.shape[0]:
                        continue
                    tn = float(np.linalg.norm(t))
                    if not np.isfinite(tn) or tn < 1e-12:
                        continue
                    score = abs(float(np.dot(t, resid))) / tn
                    if score > best_score:
                        best_score = score
                        best_i = idx

                if best_i is None:
                    break

                selected.append(best_i)
                remaining.remove(best_i)

                # Fit with constant
                T = np.column_stack([candidates[i][0] for i in selected] + [ones])
                try:
                    coef, _, _, _ = np.linalg.lstsq(T, y, rcond=None)
                    pred = T @ coef
                    m = mse(pred, y)
                    resid = y - pred
                except Exception:
                    break

                if (best is None) or (m < best[0]):
                    best = (m, selected.copy(), coef.copy(), pred.copy())

            return best

        best_greedy = greedy_fit(candidates, y, max_terms=5)

        # Choose model
        chosen = None
        if np.isfinite(mse_peaks) and (mse_peaks <= mse_lin * 0.98 or mse_peaks <= mse_lin - 1e-12):
            chosen = ("peaks", mse_peaks, coef_peaks, pred_peaks)
        if best_greedy is not None:
            m_g, sel_g, coef_g, pred_g = best_greedy
            # Prefer greedy if it significantly improves over peaks and baseline
            if chosen is None or m_g < chosen[1] * 0.98:
                chosen = ("greedy", m_g, (sel_g, coef_g), pred_g)

        if chosen is None:
            # fallback to linear
            a, b, c0 = coef_lin
            expression = f"({a:.12g})*x1 + ({b:.12g})*x2 + ({c0:.12g})"
            return {
                "expression": expression,
                "predictions": pred_lin.tolist(),
                "details": {"mse": mse_lin, "model": "linear"},
            }

        def fmt_num(v):
            if not np.isfinite(v):
                return "0.0"
            s = f"{float(v):.12g}"
            if s in ("-0", "-0.0"):
                s = "0.0"
            if ("e" not in s) and ("E" not in s) and ("." not in s):
                s = s + ".0"
            return s

        def add_term(parts, coef, term_str, is_first=False):
            if not np.isfinite(coef):
                return parts
            if abs(coef) < 1e-14:
                return parts
            sign = "-" if coef < 0 else "+"
            cabs = abs(coef)
            cstr = fmt_num(cabs)
            if is_first and sign == "+":
                parts.append(f"{cstr}*({term_str})")
            elif is_first and sign == "-":
                parts.append(f"-{cstr}*({term_str})")
            else:
                parts.append(f" {sign} {cstr}*({term_str})")
            return parts

        if chosen[0] == "peaks":
            coef = chosen[2]
            pred = chosen[3]

            c1, c2, c3, c0 = coef.tolist()

            parts = []
            ystd = float(np.std(y)) if np.isfinite(np.std(y)) else 1.0
            thresh = max(1e-12, 1e-10 * ystd)

            def add_const(parts, c0, is_first=False):
                if not np.isfinite(c0) or abs(c0) < thresh:
                    return parts
                if is_first:
                    parts.append(f"{fmt_num(c0)}")
                else:
                    if c0 < 0:
                        parts.append(f" - {fmt_num(abs(c0))}")
                    else:
                        parts.append(f" + {fmt_num(c0)}")
                return parts

            # Build expression without unnecessary leading "0.0"
            first_added = False
            for cc, tt in [
                (c1, "(1 - x1)**2*exp(-(x1**2) - (x2 + 1)**2)"),
                (c2, "(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)"),
                (c3, "exp(-(x1 + 1)**2 - x2**2)"),
            ]:
                if np.isfinite(cc) and abs(cc) >= thresh:
                    add_term(parts, cc, tt, is_first=not first_added)
                    first_added = True

            parts = add_const(parts, c0, is_first=not first_added)
            if not parts:
                parts = [fmt_num(float(np.mean(y)))]

            expression = "".join(parts)

            return {
                "expression": expression,
                "predictions": pred.tolist(),
                "details": {"mse": float(chosen[1]), "mse_linear": mse_lin, "model": "peaks_basis"},
            }

        # Greedy chosen
        sel_g, coef_g = chosen[2]
        pred = chosen[3]
        coef_g = np.asarray(coef_g, dtype=np.float64).reshape(-1)
        const = float(coef_g[-1])
        coefs_terms = coef_g[:-1]

        ystd = float(np.std(y)) if np.isfinite(np.std(y)) else 1.0
        thresh = max(1e-12, 1e-10 * ystd)

        parts = []
        first_added = False
        for idx, cc in zip(sel_g, coefs_terms):
            if not np.isfinite(cc) or abs(cc) < thresh:
                continue
            term_str = candidates[idx][1]
            add_term(parts, float(cc), term_str, is_first=not first_added)
            first_added = True

        if np.isfinite(const) and abs(const) >= thresh:
            if not first_added:
                parts.append(f"{fmt_num(const)}")
            else:
                if const < 0:
                    parts.append(f" - {fmt_num(abs(const))}")
                else:
                    parts.append(f" + {fmt_num(const)}")
            first_added = True

        if not parts:
            parts = [fmt_num(float(np.mean(y)))]

        expression = "".join(parts)

        return {
            "expression": expression,
            "predictions": pred.tolist(),
            "details": {"mse": float(chosen[1]), "mse_linear": mse_lin, "model": "greedy_library", "n_terms": int(len(sel_g))},
        }