import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = dict(kwargs)

    @staticmethod
    def _ridge_solve(A: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
        AtA = A.T @ A
        n = AtA.shape[0]
        if lam > 0:
            AtA = AtA + lam * np.eye(n, dtype=AtA.dtype)
        Aty = A.T @ y
        try:
            return np.linalg.solve(AtA, Aty)
        except np.linalg.LinAlgError:
            return np.linalg.lstsq(A, y, rcond=None)[0]

    @staticmethod
    def _fit_linear(A: np.ndarray, y: np.ndarray, ridge_factor: float = 1e-10) -> np.ndarray:
        if A.size == 0:
            return np.zeros((0,), dtype=float)
        AtA = A.T @ A
        diag_mean = float(np.mean(np.diag(AtA))) if AtA.shape[0] > 0 else 0.0
        lam = ridge_factor * diag_mean if diag_mean > 0 else 0.0
        return Solution._ridge_solve(A, y, lam)

    @staticmethod
    def _mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        d = y_true - y_pred
        return float(np.mean(d * d))

    @staticmethod
    def _poly_terms_strings_and_values(x1: np.ndarray, x2: np.ndarray, deg: int):
        terms = []
        values = []
        for total in range(1, deg + 1):
            for i in range(total, -1, -1):
                j = total - i
                # term: x1**i * x2**j
                if i == 0 and j == 0:
                    continue
                if i == 0:
                    if j == 1:
                        s = "x2"
                        v = x2
                    else:
                        s = f"x2**{j}"
                        v = x2 ** j
                elif j == 0:
                    if i == 1:
                        s = "x1"
                        v = x1
                    else:
                        s = f"x1**{i}"
                        v = x1 ** i
                else:
                    parts = []
                    if i == 1:
                        parts.append("x1")
                        v1 = x1
                    else:
                        parts.append(f"x1**{i}")
                        v1 = x1 ** i
                    if j == 1:
                        parts.append("x2")
                        v2 = x2
                    else:
                        parts.append(f"x2**{j}")
                        v2 = x2 ** j
                    s = "*".join(parts)
                    v = v1 * v2
                terms.append(s)
                values.append(v)
        return terms, values

    @staticmethod
    def _build_expression(term_strs, coeffs, include_constant=True, constant=0.0):
        pieces = []
        if include_constant:
            c0 = float(constant)
            if c0 != 0.0:
                pieces.append(f"({c0:.16g})")
        for s, a in zip(term_strs, coeffs):
            a = float(a)
            if a == 0.0:
                continue
            if s == "1":
                pieces.append(f"({a:.16g})")
            else:
                pieces.append(f"({a:.16g})*({s})")
        if not pieces:
            return "0"
        expr = " + ".join(pieces)
        expr = expr.replace("+ -", "- ")
        return expr

    @staticmethod
    def _prune_and_refit(A: np.ndarray, y: np.ndarray, term_strs, ridge_factor: float, min_rel_contrib: float):
        coeffs = Solution._fit_linear(A, y, ridge_factor=ridge_factor)
        y_std = float(np.std(y)) + 1e-12

        keep = []
        for k in range(A.shape[1]):
            contrib = abs(float(coeffs[k])) * (float(np.std(A[:, k])) + 1e-12)
            if contrib >= min_rel_contrib * y_std:
                keep.append(k)

        if len(keep) == 0:
            # keep the largest contributor
            contribs = np.abs(coeffs) * (np.std(A, axis=0) + 1e-12)
            keep = [int(np.argmax(contribs))] if contribs.size else []

        A2 = A[:, keep] if keep else A[:, :0]
        term_strs2 = [term_strs[i] for i in keep] if keep else []
        coeffs2 = Solution._fit_linear(A2, y, ridge_factor=ridge_factor) if keep else np.zeros((0,), dtype=float)
        return A2, term_strs2, coeffs2

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        x1 = X[:, 0]
        x2 = X[:, 1]
        n = X.shape[0]

        # Peaks-like basis (3 core terms)
        f1 = (1.0 - x1) ** 2 * np.exp(-(x1 ** 2) - (x2 + 1.0) ** 2)
        f2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-(x1 ** 2) - (x2 ** 2))
        f3 = np.exp(-((x1 + 1.0) ** 2) - (x2 ** 2))
        peaks_terms = [
            "(1 - x1)**2*exp(-(x1**2) - (x2 + 1)**2)",
            "(x1/5 - x1**3 - x2**5)*exp(-(x1**2) - (x2**2))",
            "exp(-(x1 + 1)**2 - (x2**2))",
        ]
        A_peaks = np.column_stack([f1, f2, f3, np.ones(n, dtype=float)])
        terms_peaks_full = peaks_terms + ["1"]

        # Combined: peaks basis + degree-3 polynomials (no extra constant term in poly; already have "1")
        poly3_strs, poly3_vals = self._poly_terms_strings_and_values(x1, x2, deg=3)
        A_comb = np.column_stack([f1, f2, f3, np.ones(n, dtype=float)] + poly3_vals)
        terms_comb_full = peaks_terms + ["1"] + poly3_strs

        # Polynomial-only degree-5 as fallback (with constant)
        poly5_strs, poly5_vals = self._poly_terms_strings_and_values(x1, x2, deg=5)
        A_poly5 = np.column_stack([np.ones(n, dtype=float)] + poly5_vals)
        terms_poly5_full = ["1"] + poly5_strs

        # Fit and prune
        ridge_factor = 1e-10
        min_rel_contrib = 2e-7

        A1, t1, c1 = self._prune_and_refit(A_peaks, y, terms_peaks_full, ridge_factor, min_rel_contrib)
        pred1 = A1 @ c1 if A1.shape[1] else np.zeros_like(y)
        mse1 = self._mse(y, pred1)

        A2, t2, c2 = self._prune_and_refit(A_comb, y, terms_comb_full, ridge_factor, min_rel_contrib)
        pred2 = A2 @ c2 if A2.shape[1] else np.zeros_like(y)
        mse2 = self._mse(y, pred2)

        A3, t3, c3 = self._prune_and_refit(A_poly5, y, terms_poly5_full, ridge_factor, min_rel_contrib)
        pred3 = A3 @ c3 if A3.shape[1] else np.zeros_like(y)
        mse3 = self._mse(y, pred3)

        # Prefer simpler model if close in MSE
        mses = [mse1, mse2, mse3]
        preds = [pred1, pred2, pred3]
        terms_list = [t1, t2, t3]
        coeffs_list = [c1, c2, c3]
        model_names = ["peaks", "peaks+poly3", "poly5"]

        best_idx = int(np.argmin(mses))
        best_mse = mses[best_idx]

        def n_terms(idx):
            # count non-constant terms approximately
            return len(terms_list[idx])

        # If peaks-only is nearly as good, choose it
        if mse1 <= 1.02 * best_mse:
            chosen = 0
        elif mse2 <= 1.01 * best_mse and n_terms(2) > n_terms(1):
            chosen = 1
        else:
            # small preference for fewer terms if mse very close
            candidates = [0, 1, 2]
            chosen = min(candidates, key=lambda i: (mses[i] * (1.0 + 0.002 * max(0, n_terms(i) - 6)), n_terms(i)))

        chosen_terms = terms_list[chosen]
        chosen_coeffs = coeffs_list[chosen]
        chosen_pred = preds[chosen]
        chosen_mse = mses[chosen]
        chosen_name = model_names[chosen]

        # Build expression: terms already include "1" as constant feature if present
        # Separate constant if we included "1"
        term_strs = []
        coeffs = []
        constant = 0.0
        for s, a in zip(chosen_terms, chosen_coeffs):
            if s == "1":
                constant += float(a)
            else:
                term_strs.append(s)
                coeffs.append(float(a))

        expression = self._build_expression(term_strs, coeffs, include_constant=True, constant=constant)

        return {
            "expression": expression,
            "predictions": chosen_pred.tolist(),
            "details": {
                "model": chosen_name,
                "mse": float(chosen_mse),
                "n_terms": int(len(term_strs) + (1 if constant != 0.0 else 0)),
            },
        }