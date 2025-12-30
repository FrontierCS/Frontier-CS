import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _fit_lstsq(cols, y):
        A = np.column_stack(cols)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        pred = A @ coeffs
        mse = float(np.mean((y - pred) ** 2))
        return coeffs, pred, mse

    @staticmethod
    def _fmt_coef(c):
        c = float(c)
        if c == 0.0:
            return "0.0"
        return f"{c:.17g}"

    @staticmethod
    def _build_expression(terms, intercept):
        expr_terms = []
        for coef, s in terms:
            if s == "1":
                continue
            expr_terms.append(f"({Solution._fmt_coef(coef)})*({s})")
        if intercept is None:
            if not expr_terms:
                return "0.0"
            return " + ".join(expr_terms)
        expr_terms.append(f"({Solution._fmt_coef(intercept)})")
        return " + ".join(expr_terms) if expr_terms else f"({Solution._fmt_coef(intercept)})"

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        n = X.shape[0]

        x1 = X[:, 0]
        x2 = X[:, 1]

        E1 = np.exp(-(x1 * x1 + (x2 + 1.0) * (x2 + 1.0)))
        E0 = np.exp(-(x1 * x1 + x2 * x2))
        E3 = np.exp(-(((x1 + 1.0) * (x1 + 1.0)) + x2 * x2))

        t1 = ((1.0 - x1) ** 2) * E1
        t2 = ((x1 / 5.0) - (x1 ** 3) - (x2 ** 5)) * E0
        e0 = E0
        t3 = E3

        x1e0 = x1 * E0
        x1_3e0 = (x1 ** 3) * E0
        x2_5e0 = (x2 ** 5) * E0

        ones = np.ones(n, dtype=float)

        col_defs = {
            "t1": (t1, "((1 - x1)**2)*exp(-((x1**2) + ((x2 + 1)**2)))"),
            "t2": (t2, "((x1/5) - (x1**3) - (x2**5))*exp(-((x1**2) + (x2**2)))"),
            "e0": (e0, "exp(-((x1**2) + (x2**2)))"),
            "t3": (t3, "exp(-(((x1 + 1)**2) + (x2**2)))"),
            "x1e0": (x1e0, "(x1)*exp(-((x1**2) + (x2**2)))"),
            "x1_3e0": (x1_3e0, "(x1**3)*exp(-((x1**2) + (x2**2)))"),
            "x2_5e0": (x2_5e0, "(x2**5)*exp(-((x1**2) + (x2**2)))"),
            "1": (ones, "1"),
        }

        candidates = [
            ("peaks", ["t1", "t2", "t3", "1"], 3),
            ("peaks_e0", ["t1", "t2", "e0", "t3", "1"], 4),
            ("split", ["t1", "x1e0", "x1_3e0", "x2_5e0", "t3", "1"], 5),
            ("split_e0", ["t1", "x1e0", "x1_3e0", "x2_5e0", "e0", "t3", "1"], 6),
        ]

        fits = []
        for name, keys, complexity in candidates:
            cols = [col_defs[k][0] for k in keys]
            coeffs, pred, mse = self._fit_lstsq(cols, y)
            fits.append((mse, complexity, name, keys, coeffs, pred))

        fits.sort(key=lambda t: (t[0], t[1]))
        best_mse = fits[0][0]
        y_scale = float(np.mean(y * y)) if n > 0 else 1.0
        tol = max(best_mse * 0.01, 1e-12 * (y_scale + 1.0))

        eligible = [f for f in fits if f[0] <= best_mse + tol]
        chosen = min(eligible, key=lambda t: (t[1], t[0]))
        mse, complexity, name, keys, coeffs, pred = chosen

        # Prune tiny coefficients and refit (keep intercept always if present)
        max_y = float(np.sqrt(y_scale + 1e-30))
        thresh = 1e-10 * max(1.0, max_y)

        def refit_with_keys(keys_now):
            cols_now = [col_defs[k][0] for k in keys_now]
            return self._fit_lstsq(cols_now, y)

        keys_now = list(keys)
        for _ in range(3):
            if not keys_now:
                break
            coeffs_now, pred_now, mse_now = refit_with_keys(keys_now)
            if keys_now and keys_now[-1] == "1":
                intercept_idx = len(keys_now) - 1
                mask = [True] * len(keys_now)
                for i, k in enumerate(keys_now[:-1]):
                    if abs(coeffs_now[i]) < thresh:
                        mask[i] = False
                new_keys = [k for keep, k in zip(mask, keys_now) if keep]
                if new_keys == keys_now:
                    keys, coeffs, pred, mse = keys_now, coeffs_now, pred_now, mse_now
                    break
                keys_now = new_keys
                continue
            else:
                mask = [abs(c) >= thresh for c in coeffs_now]
                new_keys = [k for keep, k in zip(mask, keys_now) if keep]
                if new_keys == keys_now:
                    keys, coeffs, pred, mse = keys_now, coeffs_now, pred_now, mse_now
                    break
                keys_now = new_keys

        # Build final expression
        terms = []
        intercept = None
        for k, c in zip(keys, coeffs):
            if k == "1":
                intercept = float(c)
            else:
                terms.append((float(c), col_defs[k][1]))

        expression = self._build_expression(terms, intercept)

        details = {
            "model": name,
            "mse": mse,
            "complexity": int(len(terms)),
        }

        return {
            "expression": expression,
            "predictions": pred.tolist() if pred is not None else None,
            "details": details,
        }