import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def _fmt(self, x):
        if not np.isfinite(x):
            x = 0.0
        if abs(x) < 1e-14:
            x = 0.0
        return f"{x:.12g}"

    def _build_peaks_classic(self, x1, x2):
        E1 = np.exp(-(x1**2 + (x2 + 1.0)**2))
        E2 = np.exp(-(x1**2 + x2**2))
        E3 = np.exp(-((x1 + 1.0)**2 + x2**2))
        t1 = (1.0 - x1)**2 * E1
        t2 = (x1 / 5.0 - x1**3 - x2**5) * E2
        t3 = E3
        return t1, t2, t3

    def _classic_model(self, x1, x2, y):
        t1, t2, t3 = self._build_peaks_classic(x1, x2)
        n = x1.shape[0]
        A = np.column_stack([t1, t2, t3, np.ones(n)])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        preds = A @ coeffs

        a, b, c, d = coeffs
        a_s = self._fmt(a)
        b_s = self._fmt(b)
        c_s = self._fmt(c)
        d_s = self._fmt(d)

        expr = (
            f"{a_s}*((1 - x1)**2*exp(-(x1**2 + (x2 + 1)**2))) + "
            f"{b_s}*((x1/5 - x1**3 - x2**5)*exp(-(x1**2 + x2**2))) + "
            f"{c_s}*exp(-((x1 + 1)**2 + x2**2)) + {d_s}"
        )
        return expr, preds

    def _feature_set(self, x1, x2):
        # Base exponentials
        E1 = np.exp(-(x1**2 + (x2 + 1.0)**2))
        E2 = np.exp(-(x1**2 + x2**2))
        E3 = np.exp(-((x1 + 1.0)**2 + x2**2))

        features = []
        # Classic-like structured terms
        features.append((
            "(1 - x1)**2 * exp(-(x1**2 + (x2 + 1)**2))",
            (1.0 - x1)**2 * E1
        ))
        features.append((
            "exp(-((x1 + 1)**2 + x2**2))",
            E3
        ))
        # Decomposed E2 polynomial parts
        features.append((
            "x1 * exp(-(x1**2 + x2**2))",
            x1 * E2
        ))
        features.append((
            "x1**3 * exp(-(x1**2 + x2**2))",
            (x1**3) * E2
        ))
        features.append((
            "x2**5 * exp(-(x1**2 + x2**2))",
            (x2**5) * E2
        ))
        features.append((
            "exp(-(x1**2 + x2**2))",
            E2
        ))
        return features

    def _selected_model(self, x1, x2, y, max_terms=3):
        feats = self._feature_set(x1, x2)
        n = x1.shape[0]

        # Initial fit with all features + intercept
        F_all = np.column_stack([arr for (_, arr) in feats] + [np.ones(n)])
        coeffs_all, _, _, _ = np.linalg.lstsq(F_all, y, rcond=None)
        coeffs = coeffs_all[:-1]
        intercept = coeffs_all[-1]

        # Scoring features by |coef|*std
        stds = np.array([np.std(arr) if np.std(arr) > 1e-12 else 1e-12 for (_, arr) in feats])
        scores = np.abs(coeffs) * stds
        idx_sorted = np.argsort(-scores)

        # Select top features with non-zero contribution
        selected_idx = []
        for idx in idx_sorted:
            if len(selected_idx) >= max_terms:
                break
            if np.abs(coeffs[idx]) > 1e-12:
                selected_idx.append(idx)

        # If none selected (degenerate), fallback to the top-scoring regardless
        if len(selected_idx) == 0:
            selected_idx = idx_sorted[:max_terms].tolist()

        # Refit with selected features + intercept
        F_sel = np.column_stack([feats[i][1] for i in selected_idx] + [np.ones(n)])
        coeffs_sel, _, _, _ = np.linalg.lstsq(F_sel, y, rcond=None)
        coef_terms = coeffs_sel[:-1]
        intercept_sel = coeffs_sel[-1]

        # Build expression string
        parts = []
        for coef, i in zip(coef_terms, selected_idx):
            coef_s = self._fmt(coef)
            expr_i = feats[i][0]
            parts.append(f"{coef_s}*({expr_i})")
        parts.append(self._fmt(intercept_sel))
        expression = " + ".join(parts)

        predictions = F_sel @ coeffs_sel
        return expression, predictions

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0].astype(float)
        x2 = X[:, 1].astype(float)

        # Candidate 1: Classic peaks-structured model
        expr1, preds1 = self._classic_model(x1, x2, y)
        mse1 = float(np.mean((y - preds1) ** 2))

        # Candidate 2: Selected features model
        expr2, preds2 = self._selected_model(x1, x2, y, max_terms=3)
        mse2 = float(np.mean((y - preds2) ** 2))

        # Choose the better model (lower MSE). If tie, prefer simpler classic version.
        if mse1 <= mse2 * 1.001:
            expression = expr1
            predictions = preds1
        else:
            expression = expr2
            predictions = preds2

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
