import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0].astype(float)
        x2 = X[:, 1].astype(float)
        y = y.astype(float)
        r = np.sqrt(x1 * x1 + x2 * x2)

        # Precompute powers of r
        r1 = r
        r2 = r * r

        # Helper to build feature matrix
        def build_features(kind, k1=None, k2=None, d=0.0, deg1=2, deg2=2, bias=True):
            g = 1.0 / (1.0 + d * r1)  # denominator modulation
            cols = []

            if kind in ("kr", "both"):
                s1 = np.sin(k1 * r1)
                c1 = np.cos(k1 * r1)
                # degree deg1 polynomial times sin/cos
                # degrees: 0..deg1
                cols.extend([s1, r1 * s1, r2 * s1][:deg1 + 1])
                cols.extend([c1, r1 * c1, r2 * c1][:deg1 + 1])

            if kind in ("kr2", "both"):
                s2v = np.sin(k2 * r2)
                c2v = np.cos(k2 * r2)
                cols.extend([s2v, r1 * s2v, r2 * s2v][:deg2 + 1])
                cols.extend([c2v, r1 * c2v, r2 * c2v][:deg2 + 1])

            if bias:
                cols.append(np.ones_like(r))

            if not cols:
                A0 = np.ones((r.shape[0], 1))
            else:
                A0 = np.column_stack(cols)
            A = A0 * g[:, None]
            return A, g

        def fit_and_eval(kind, k1=None, k2=None, d=0.0, deg1=2, deg2=2, bias=True):
            A, g = build_features(kind, k1=k1, k2=k2, d=d, deg1=deg1, deg2=deg2, bias=bias)
            # Solve least squares
            c, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            yhat = A @ c
            mse = float(np.mean((y - yhat) ** 2))
            return mse, c, yhat

        # Search grids
        d_list_main = [0.0, 0.1, 0.25, 0.5]
        # KR: sin(k*r), cos(k*r)
        k_list_kr = np.arange(0.5, 15.0001, 0.25)  # 0.5 to 15.0
        # KR2: sin(k*r^2), cos(k*r^2)
        k_list_kr2 = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
        # BOTH coarse
        k1_list_both = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 12.0]
        k2_list_both = [0.5, 1.0, 2.0]
        d_list_both = [0.0, 0.25]

        best = {
            "mse": np.inf,
            "kind": None,
            "k1": None,
            "k2": None,
            "d": 0.0,
            "deg1": None,
            "deg2": None,
            "bias": True,
            "coeffs": None,
            "pred": None,
        }

        # Model 1: 'kr' with deg 2
        for d in d_list_main:
            for k in k_list_kr:
                mse, coeffs, pred = fit_and_eval("kr", k1=k, k2=None, d=d, deg1=2, deg2=0, bias=True)
                if mse < best["mse"]:
                    best.update(dict(mse=mse, kind="kr", k1=k, k2=None, d=d, deg1=2, deg2=0, coeffs=coeffs, pred=pred))

        # Model 2: 'kr2' with deg 2
        for d in d_list_main:
            for k in k_list_kr2:
                mse, coeffs, pred = fit_and_eval("kr2", k1=None, k2=k, d=d, deg1=0, deg2=2, bias=True)
                if mse < best["mse"]:
                    best.update(dict(mse=mse, kind="kr2", k1=None, k2=k, d=d, deg1=0, deg2=2, coeffs=coeffs, pred=pred))

        # Model 3: 'both' with lower degree to control complexity (deg1=1, deg2=1)
        for d in d_list_both:
            for k1 in k1_list_both:
                for k2 in k2_list_both:
                    mse, coeffs, pred = fit_and_eval("both", k1=k1, k2=k2, d=d, deg1=1, deg2=1, bias=True)
                    if mse < best["mse"]:
                        best.update(dict(mse=mse, kind="both", k1=k1, k2=k2, d=d, deg1=1, deg2=1, coeffs=coeffs, pred=pred))

        # Refinement around the best k(s)
        def refine_k(best_state):
            if best_state["kind"] == "kr":
                k0 = best_state["k1"]
                d = best_state["d"]
                # local fine search around k0
                deltas = np.linspace(-0.5, 0.5, 11)
                improved = False
                for dk in deltas:
                    k = max(0.05, k0 + dk)
                    mse, coeffs, pred = fit_and_eval("kr", k1=k, k2=None, d=d, deg1=2, deg2=0, bias=True)
                    if mse < best_state["mse"]:
                        best_state.update(dict(mse=mse, k1=k, coeffs=coeffs, pred=pred))
                        improved = True
                return improved
            elif best_state["kind"] == "kr2":
                k0 = best_state["k2"]
                d = best_state["d"]
                deltas = np.linspace(-0.3, 0.3, 9)
                improved = False
                for dk in deltas:
                    k = max(0.05, k0 + dk)
                    mse, coeffs, pred = fit_and_eval("kr2", k1=None, k2=k, d=d, deg1=0, deg2=2, bias=True)
                    if mse < best_state["mse"]:
                        best_state.update(dict(mse=mse, k2=k, coeffs=coeffs, pred=pred))
                        improved = True
                return improved
            elif best_state["kind"] == "both":
                k10 = best_state["k1"]
                k20 = best_state["k2"]
                d = best_state["d"]
                deltas = [-0.3, -0.15, 0.0, 0.15, 0.3]
                improved = False
                for dk1 in deltas:
                    for dk2 in deltas:
                        k1 = max(0.05, k10 + dk1)
                        k2 = max(0.05, k20 + dk2)
                        mse, coeffs, pred = fit_and_eval("both", k1=k1, k2=k2, d=d, deg1=1, deg2=1, bias=True)
                        if mse < best_state["mse"]:
                            best_state.update(dict(mse=mse, k1=k1, k2=k2, coeffs=coeffs, pred=pred))
                            improved = True
                return improved
            else:
                return False

        # Perform a couple of refinement passes
        for _ in range(2):
            changed = refine_k(best)
            if not changed:
                break

        # Build expression string
        def fmt_num(v):
            # format float with sufficient precision but compact
            if np.isfinite(v):
                return f"{float(v):.12g}"
            else:
                return "0.0"

        r_expr = "(x1**2 + x2**2)**0.5"
        parts = []

        coeffs = best["coeffs"]
        idx = 0

        def poly_from_coeffs(coeff_list):
            terms = []
            for p, c in enumerate(coeff_list):
                if abs(c) < 1e-10:
                    continue
                cn = fmt_num(c)
                if p == 0:
                    terms.append(f"{cn}")
                elif p == 1:
                    terms.append(f"{cn}*{r_expr}")
                else:
                    terms.append(f"{cn}*({r_expr}**{p})")
            if not terms:
                return "0.0"
            # Combine terms; negative signs included in cn
            return "(" + " + ".join(terms) + ")"

        # Extract and build according to kind
        if best["kind"] == "kr":
            deg = best["deg1"]
            # sin poly deg+1
            sin_coeffs = coeffs[idx:idx + (deg + 1)]
            idx += (deg + 1)
            cos_coeffs = coeffs[idx:idx + (deg + 1)]
            idx += (deg + 1)
            bias_c = coeffs[idx] if idx < len(coeffs) else 0.0

            poly_sin = poly_from_coeffs(sin_coeffs)
            poly_cos = poly_from_coeffs(cos_coeffs)

            sin_arg = f"{fmt_num(best['k1'])}*{r_expr}"
            sin_part = None if poly_sin == "0.0" else f"{poly_sin}*sin({sin_arg})"
            cos_part = None if poly_cos == "0.0" else f"{poly_cos}*cos({sin_arg})"
            if sin_part:
                parts.append(sin_part)
            if cos_part:
                parts.append(cos_part)
            if abs(bias_c) >= 1e-10:
                parts.append(fmt_num(bias_c))

        elif best["kind"] == "kr2":
            deg = best["deg2"]
            sin_coeffs = coeffs[idx:idx + (deg + 1)]
            idx += (deg + 1)
            cos_coeffs = coeffs[idx:idx + (deg + 1)]
            idx += (deg + 1)
            bias_c = coeffs[idx] if idx < len(coeffs) else 0.0

            poly_sin = poly_from_coeffs(sin_coeffs)
            poly_cos = poly_from_coeffs(cos_coeffs)

            sin_arg = f"{fmt_num(best['k2'])}*({r_expr}**2)"
            sin_part = None if poly_sin == "0.0" else f"{poly_sin}*sin({sin_arg})"
            cos_part = None if poly_cos == "0.0" else f"{poly_cos}*cos({sin_arg})"
            if sin_part:
                parts.append(sin_part)
            if cos_part:
                parts.append(cos_part)
            if abs(bias_c) >= 1e-10:
                parts.append(fmt_num(bias_c))

        elif best["kind"] == "both":
            deg1 = best["deg1"]
            deg2 = best["deg2"]

            sin1_coeffs = coeffs[idx:idx + (deg1 + 1)]
            idx += (deg1 + 1)
            cos1_coeffs = coeffs[idx:idx + (deg1 + 1)]
            idx += (deg1 + 1)

            sin2_coeffs = coeffs[idx:idx + (deg2 + 1)]
            idx += (deg2 + 1)
            cos2_coeffs = coeffs[idx:idx + (deg2 + 1)]
            idx += (deg2 + 1)

            bias_c = coeffs[idx] if idx < len(coeffs) else 0.0

            poly_sin1 = poly_from_coeffs(sin1_coeffs)
            poly_cos1 = poly_from_coeffs(cos1_coeffs)
            poly_sin2 = poly_from_coeffs(sin2_coeffs)
            poly_cos2 = poly_from_coeffs(cos2_coeffs)

            arg1 = f"{fmt_num(best['k1'])}*{r_expr}"
            arg2 = f"{fmt_num(best['k2'])}*({r_expr}**2)"

            s1 = None if poly_sin1 == "0.0" else f"{poly_sin1}*sin({arg1})"
            c1 = None if poly_cos1 == "0.0" else f"{poly_cos1}*cos({arg1})"
            s2 = None if poly_sin2 == "0.0" else f"{poly_sin2}*sin({arg2})"
            c2 = None if poly_cos2 == "0.0" else f"{poly_cos2}*cos({arg2})"

            for part in (s1, c1, s2, c2):
                if part:
                    parts.append(part)
            if abs(bias_c) >= 1e-10:
                parts.append(fmt_num(bias_c))

        # Combine numerator parts
        if not parts:
            numerator_expr = "0.0"
        else:
            numerator_expr = "(" + " + ".join(parts) + ")"

        # Apply g
        if best["d"] != 0.0:
            g_expr = f"1.0/(1.0 + {fmt_num(best['d'])}*{r_expr})"
            final_expr = f"{g_expr}*{numerator_expr}"
        else:
            final_expr = numerator_expr

        predictions = best["pred"].tolist() if best["pred"] is not None else None

        details = {
            "mse": best["mse"],
            "kind": best["kind"],
            "k1": best["k1"],
            "k2": best["k2"],
            "d": best["d"],
        }

        return {
            "expression": final_expr,
            "predictions": predictions,
            "details": details,
        }