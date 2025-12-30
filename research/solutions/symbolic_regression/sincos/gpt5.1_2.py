import numpy as np


class Solution:
    def __init__(self, **kwargs):
        # Maximum number of non-constant basis functions to consider initially
        self.max_nonconst = kwargs.get("max_nonconst", 8)

    def _format_coef(self, c: float) -> str:
        s = f"{c:.10g}"
        if s == "-0":
            s = "0"
        return s

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        n_samples = X.shape[0]
        if n_samples == 0 or X.shape[1] < 2:
            expression = "0"
            return {"expression": expression, "predictions": [], "details": {}}

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Precompute basic trig and interaction terms
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)

        s1_2 = np.sin(2.0 * x1)
        c1_2 = np.cos(2.0 * x1)
        s2_2 = np.sin(2.0 * x2)
        c2_2 = np.cos(2.0 * x2)

        x1_plus_x2 = x1 + x2
        x1_minus_x2 = x1 - x2
        s1p2 = np.sin(x1_plus_x2)
        c1p2 = np.cos(x1_plus_x2)
        s1m2 = np.sin(x1_minus_x2)
        c1m2 = np.cos(x1_minus_x2)

        x1x2 = x1 * x2
        s_x1x2 = np.sin(x1x2)
        c_x1x2 = np.cos(x1x2)

        # Define feature expressions and their values
        feature_exprs = []
        feature_vals = []

        # 1. Linear terms
        feature_exprs.append("x1")
        feature_vals.append(x1)

        feature_exprs.append("x2")
        feature_vals.append(x2)

        # 2. Basic trig of each variable
        feature_exprs.append("sin(x1)")
        feature_vals.append(s1)

        feature_exprs.append("cos(x1)")
        feature_vals.append(c1)

        feature_exprs.append("sin(2*x1)")
        feature_vals.append(s1_2)

        feature_exprs.append("cos(2*x1)")
        feature_vals.append(c1_2)

        feature_exprs.append("sin(x2)")
        feature_vals.append(s2)

        feature_exprs.append("cos(x2)")
        feature_vals.append(c2)

        feature_exprs.append("sin(2*x2)")
        feature_vals.append(s2_2)

        feature_exprs.append("cos(2*x2)")
        feature_vals.append(c2_2)

        # 3. Sum/difference combinations
        feature_exprs.append("sin(x1 + x2)")
        feature_vals.append(s1p2)

        feature_exprs.append("cos(x1 + x2)")
        feature_vals.append(c1p2)

        feature_exprs.append("sin(x1 - x2)")
        feature_vals.append(s1m2)

        feature_exprs.append("cos(x1 - x2)")
        feature_vals.append(c1m2)

        # 4. Product and trig of product
        feature_exprs.append("x1*x2")
        feature_vals.append(x1x2)

        feature_exprs.append("sin(x1*x2)")
        feature_vals.append(s_x1x2)

        feature_exprs.append("cos(x1*x2)")
        feature_vals.append(c_x1x2)

        # 5. Products of trig terms
        feature_exprs.append("sin(x1)*sin(x2)")
        feature_vals.append(s1 * s2)

        feature_exprs.append("sin(x1)*cos(x2)")
        feature_vals.append(s1 * c2)

        feature_exprs.append("cos(x1)*sin(x2)")
        feature_vals.append(c1 * s2)

        feature_exprs.append("cos(x1)*cos(x2)")
        feature_vals.append(c1 * c2)

        # 6. Mixed trig-linear products
        feature_exprs.append("sin(x1)*x2")
        feature_vals.append(s1 * x2)

        feature_exprs.append("sin(x2)*x1")
        feature_vals.append(s2 * x1)

        feature_exprs.append("cos(x1)*x2")
        feature_vals.append(c1 * x2)

        feature_exprs.append("cos(x2)*x1")
        feature_vals.append(c2 * x1)

        m = len(feature_exprs)

        # Build full design matrix with intercept in column 0
        A_full = np.empty((n_samples, m + 1), dtype=float)
        A_full[:, 0] = 1.0
        for j, vals in enumerate(feature_vals, start=1):
            A_full[:, j] = vals

        # Helper to fit model and compute BIC
        def fit_model(cols: np.ndarray):
            A = A_full[:, cols]
            coefs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            y_pred = A @ coefs
            resid = y - y_pred
            SSE = float(resid @ resid)
            if not np.isfinite(SSE) or SSE <= 0.0:
                SSE = 1e-12
            mse = SSE / n_samples
            p = len(cols)
            if n_samples > 0:
                BIC = n_samples * np.log(SSE / n_samples) + p * np.log(n_samples)
            else:
                BIC = np.inf
            return coefs, y_pred, mse, BIC

        # Initial full fit to rank features by importance
        all_cols = np.arange(m + 1, dtype=int)
        full_coefs, _, _, _ = fit_model(all_cols)

        coefs_nonconst = full_coefs[1:]
        stds_nonconst = np.std(A_full[:, 1:], axis=0)
        importances = np.abs(coefs_nonconst) * stds_nonconst
        order = np.argsort(-importances)  # descending

        max_nonconst = min(self.max_nonconst, m, max(0, n_samples - 1))

        best_BIC = None
        best_cols = None
        best_coefs = None
        best_y_pred = None
        best_mse = None

        # Forward selection over ranked features using BIC
        for k_nonconst in range(0, max_nonconst + 1):
            if k_nonconst == 0:
                cols = np.array([0], dtype=int)
            else:
                selected = order[:k_nonconst] + 1  # shift because of intercept at 0
                cols = np.concatenate(([0], selected.astype(int)))
            coefs_k, y_pred_k, mse_k, BIC_k = fit_model(cols)
            if (best_BIC is None) or (BIC_k < best_BIC):
                best_BIC = BIC_k
                best_cols = cols
                best_coefs = coefs_k
                best_y_pred = y_pred_k
                best_mse = mse_k

        # Backward elimination to refine model
        improved = True
        while improved and len(best_cols) > 1:
            improved = False
            base_cols = best_cols
            base_BIC = best_BIC

            best_local_BIC = base_BIC
            best_local_cols = base_cols
            best_local_coefs = best_coefs
            best_local_y_pred = best_y_pred
            best_local_mse = best_mse

            # Indices in base_cols that correspond to non-intercept features
            candidate_positions = [i for i, col in enumerate(base_cols) if col != 0]

            for pos in candidate_positions:
                cols_candidate = np.delete(base_cols, pos)
                coefs_cand, y_pred_cand, mse_cand, BIC_cand = fit_model(cols_candidate)
                if BIC_cand + 1e-9 < best_local_BIC:
                    best_local_BIC = BIC_cand
                    best_local_cols = cols_candidate
                    best_local_coefs = coefs_cand
                    best_local_y_pred = y_pred_cand
                    best_local_mse = mse_cand
                    improved = True

            if improved:
                best_BIC = best_local_BIC
                best_cols = best_local_cols
                best_coefs = best_local_coefs
                best_y_pred = best_local_y_pred
                best_mse = best_local_mse

        # Build expression string from final model
        all_exprs = ["1"] + feature_exprs

        intercept_coef = 0.0
        nonconst_terms = []

        for i, col in enumerate(best_cols):
            coef = float(best_coefs[i])
            if col == 0:
                intercept_coef = coef
            else:
                if coef != 0.0:
                    nonconst_terms.append((coef, all_exprs[col]))

        pieces = []

        # Always include intercept (may be effectively zero)
        intercept_str = self._format_coef(intercept_coef)
        pieces.append(intercept_str)

        # Add non-constant terms
        for coef, expr_str in nonconst_terms:
            coef_abs = abs(coef)
            coef_abs_str = self._format_coef(coef_abs)
            if coef_abs_str == "1":
                term = expr_str
            else:
                term = f"{coef_abs_str}*{expr_str}"

            if coef >= 0:
                pieces.append(f"+ {term}")
            else:
                pieces.append(f"- {term}")

        expression = " ".join(pieces).strip()

        predictions = best_y_pred.tolist() if best_y_pred is not None else None

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }