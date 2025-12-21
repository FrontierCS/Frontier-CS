import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.max_terms = int(kwargs.get("max_terms", 6))
        self.random_state = int(kwargs.get("random_state", 42))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).ravel()
        n, d = X.shape
        if d != 2:
            raise ValueError("X must have shape (n, 2)")
        # Build features
        terms = self._build_terms(X)
        # Forward selection on train/val split
        selected = self._forward_select(X, y, terms)
        # Final fit on all data
        coefs, intercept = self._fit_all(X, y, terms, selected)
        # Round coefficients and refit intercept
        coefs_rounded, intercept_rounded = self._round_and_refit_intercept(X, y, terms, selected, coefs, intercept)
        # Build expression and predictions for this model
        expression_model = self._build_expression(terms, selected, coefs_rounded, intercept_rounded)
        preds_model = self._predict_with_terms(X, terms, selected, coefs_rounded, intercept_rounded)

        # Try very simple candidate expressions and prefer them if comparable
        simple_expr, simple_preds = self._try_simple_forms(X, y)
        mse_model = self._mse(y, preds_model)
        mse_simple = self._mse(y, simple_preds)

        # Prefer simpler expression if it achieves virtually the same error
        # Use a very small tolerance relative to variance to avoid degrading fit
        var_y = np.var(y) + 1e-12
        tol = 1e-8 * var_y + 1e-12
        if mse_simple <= mse_model + tol:
            expression = simple_expr
            predictions = simple_preds
        else:
            expression = expression_model
            predictions = preds_model

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }

    def _build_terms(self, X):
        x1 = X[:, 0]
        x2 = X[:, 1]
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)
        s_p = np.sin(x1 + x2)
        s_m = np.sin(x1 - x2)
        c_p = np.cos(x1 + x2)
        c_m = np.cos(x1 - x2)

        # Define features with their internal complexity metadata
        # unary_count: number of sin/cos calls inside the term
        # bin_internal: number of binary operations inside the term (e.g., * or +/- inside sin/cos)
        terms = {
            "x1": {"values": x1, "unary": 0, "bin_internal": 0},
            "x2": {"values": x2, "unary": 0, "bin_internal": 0},
            "sin(x1)": {"values": s1, "unary": 1, "bin_internal": 0},
            "cos(x1)": {"values": c1, "unary": 1, "bin_internal": 0},
            "sin(x2)": {"values": s2, "unary": 1, "bin_internal": 0},
            "cos(x2)": {"values": c2, "unary": 1, "bin_internal": 0},
            "sin(x1 + x2)": {"values": s_p, "unary": 1, "bin_internal": 1},
            "sin(x1 - x2)": {"values": s_m, "unary": 1, "bin_internal": 1},
            "cos(x1 + x2)": {"values": c_p, "unary": 1, "bin_internal": 1},
            "cos(x1 - x2)": {"values": c_m, "unary": 1, "bin_internal": 1},
            "sin(x1)*cos(x2)": {"values": s1 * c2, "unary": 2, "bin_internal": 1},
            "sin(x1)*sin(x2)": {"values": s1 * s2, "unary": 2, "bin_internal": 1},
            "cos(x1)*cos(x2)": {"values": c1 * c2, "unary": 2, "bin_internal": 1},
            "cos(x1)*sin(x2)": {"values": c1 * s2, "unary": 2, "bin_internal": 1},
        }
        # Preferred ordering for nicer expressions
        self._preferred_order = [
            "sin(x1)", "cos(x2)", "cos(x1)", "sin(x2)",
            "x1", "x2",
            "sin(x1 + x2)", "cos(x1 + x2)", "sin(x1 - x2)", "cos(x1 - x2)",
            "sin(x1)*cos(x2)", "sin(x1)*sin(x2)", "cos(x1)*cos(x2)", "cos(x1)*sin(x2)",
        ]
        return terms

    def _forward_select(self, X, y, terms):
        rng = np.random.default_rng(self.random_state)
        n = X.shape[0]
        n_val = max(int(0.2 * n), 1)
        idx = rng.permutation(n)
        val_idx = idx[:n_val]
        tr_idx = idx[n_val:] if n_val < n else idx[:0]

        y_tr = y[tr_idx] if tr_idx.size else y
        y_val = y[val_idx] if val_idx.size else y

        ones_tr = np.ones_like(y_tr)
        ones_val = np.ones_like(y_val)

        selected = []
        remaining = list(terms.keys())

        # Start with intercept-only model
        if tr_idx.size:
            c0 = np.mean(y_tr)
            pred_val = np.full_like(y_val, c0)
        else:
            c0 = np.mean(y)
            pred_val = np.full_like(y_val, c0) if val_idx.size else np.full_like(y, c0)

        best_mse = self._mse(y_val, pred_val) if val_idx.size else self._mse(y, np.full_like(y, c0))

        # Build matrices incrementally
        F_tr = np.zeros((y_tr.shape[0], 0)) if tr_idx.size else np.zeros((y.shape[0], 0))
        F_val = np.zeros((y_val.shape[0], 0)) if val_idx.size else np.zeros((y.shape[0], 0))

        # Selection loop
        max_terms = min(self.max_terms, len(remaining))
        for _ in range(max_terms):
            best_candidate = None
            best_candidate_mse = np.inf
            best_candidate_coef_count = None

            for name in remaining:
                f_tr = terms[name]["values"][tr_idx] if tr_idx.size else terms[name]["values"]
                f_val = terms[name]["values"][val_idx] if val_idx.size else terms[name]["values"]

                A_tr = np.column_stack([F_tr, f_tr, ones_tr]) if tr_idx.size else np.column_stack([F_tr, f_tr, np.ones_like(y)])
                A_val = np.column_stack([F_val, f_val, ones_val]) if val_idx.size else np.column_stack([F_val, f_val, np.ones_like(y)])

                coef, *_ = np.linalg.lstsq(A_tr, y_tr if tr_idx.size else y, rcond=None)
                pred = A_val @ coef
                mse = self._mse(y_val if val_idx.size else y, pred)

                # Tie-breaker: prefer simpler candidate term if MSE equal within tiny tolerance
                # Simplicity metric: 2*bin_internal + unary
                simplicity = 2 * terms[name]["bin_internal"] + terms[name]["unary"]
                if mse < best_candidate_mse - 1e-14:
                    best_candidate_mse = mse
                    best_candidate = name
                    best_candidate_coef_count = simplicity
                elif abs(mse - best_candidate_mse) <= 1e-14:
                    if simplicity < (best_candidate_coef_count if best_candidate_coef_count is not None else 1e9):
                        best_candidate_mse = mse
                        best_candidate = name
                        best_candidate_coef_count = simplicity

            # Check improvement
            var_y = np.var(y_val if val_idx.size else y) + 1e-12
            tol_improve = 1e-8 * var_y + 1e-12
            if best_candidate is None or best_candidate_mse > best_mse - tol_improve:
                break

            # Accept candidate
            selected.append(best_candidate)
            remaining.remove(best_candidate)

            # Update matrices with accepted feature
            f_tr_add = terms[best_candidate]["values"][tr_idx] if tr_idx.size else terms[best_candidate]["values"]
            f_val_add = terms[best_candidate]["values"][val_idx] if val_idx.size else terms[best_candidate]["values"]

            F_tr = np.column_stack([F_tr, f_tr_add]) if F_tr.size else f_tr_add.reshape(-1, 1)
            F_val = np.column_stack([F_val, f_val_add]) if F_val.size else f_val_add.reshape(-1, 1)
            best_mse = best_candidate_mse

        return selected

    def _fit_all(self, X, y, terms, selected):
        if not selected:
            # Intercept-only
            return np.zeros(0, dtype=float), float(np.mean(y))
        F = np.column_stack([terms[name]["values"] for name in selected])
        A = np.column_stack([F, np.ones(len(y))])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        coefs = coef[:-1]
        intercept = coef[-1]
        return coefs, float(intercept)

    def _round_and_refit_intercept(self, X, y, terms, selected, coefs, intercept):
        # Round coefficients to simple values if very close, then refit intercept only
        if coefs.size == 0:
            # Only intercept
            return coefs, intercept

        rounded = coefs.copy()
        for i, c in enumerate(coefs):
            rounded[i] = self._round_coef(c)

        # Refit intercept only with rounded coefficients
        F = np.column_stack([terms[name]["values"] for name in selected])
        # intercept minimizing squared error with fixed coefficients
        residual = y - F @ rounded
        new_intercept = float(np.mean(residual))

        # Optionally round intercept to zero if negligible and error increase negligible
        var_y = np.var(y) + 1e-12
        tol = 1e-8 * var_y + 1e-12
        mse_with_intercept = self._mse(y, residual - new_intercept + new_intercept)  # equals mse of residual
        mse_without_intercept = self._mse(y, F @ rounded)
        if abs(mse_without_intercept - mse_with_intercept) <= tol and abs(new_intercept) <= 1e-6:
            new_intercept = 0.0

        return rounded, new_intercept

    def _round_coef(self, c):
        # Round coefficients to nearby simple values if within small tolerance
        c = float(c)
        # If extremely small, zero it
        if abs(c) < 1e-9:
            return 0.0
        candidates = [
            -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0,
            0.5, 1.0, 1.5, 2.0, 2.5, 3.0
        ]
        tol = max(5e-3, 0.01 * max(1.0, abs(c)))
        best = c
        for k in candidates:
            if abs(c - k) <= tol:
                best = k
                break
        return best

    def _float_to_str(self, x):
        x = float(x)
        if abs(x - round(x)) < 1e-12 * max(1.0, abs(x)):
            return str(int(round(x)))
        return f"{x:.12g}"

    def _build_expression(self, terms, selected, coefs, intercept):
        # Order terms by preferred order
        if not selected:
            return self._float_to_str(intercept)
        order_map = {name: i for i, name in enumerate(self._preferred_order)}
        selected_sorted = sorted(selected, key=lambda n: order_map.get(n, len(self._preferred_order) + 1))

        # Map names to coefs accordingly
        name_to_coef = {name: coefs[i] for i, name in enumerate(selected)}
        parts = []
        # Include intercept if not zero
        if abs(intercept) > 0.0:
            parts.append(self._float_to_str(intercept))

        for idx, name in enumerate(selected_sorted):
            c = float(name_to_coef[name])
            if abs(c) < 1e-12:
                continue
            term_str = name
            sign = "-" if c < 0 else "+"
            mag = abs(c)
            if abs(mag - 1.0) < 1e-12:
                piece = term_str
            else:
                piece = self._float_to_str(mag) + "*" + term_str
            if not parts:
                # First term
                if sign == "-":
                    parts.append("-" + piece)
                else:
                    parts.append(piece)
            else:
                parts.append((" - " if sign == "-" else " + ") + piece)

        if not parts:
            return "0"
        return "".join(parts)

    def _predict_with_terms(self, X, terms, selected, coefs, intercept):
        if not selected:
            return np.full(X.shape[0], intercept, dtype=float)
        F = np.column_stack([terms[name]["values"] for name in selected])
        return F @ coefs + intercept

    def _mse(self, y_true, y_pred):
        diff = y_true - y_pred
        return float(np.mean(diff * diff))

    def _try_simple_forms(self, X, y):
        x1 = X[:, 0]
        x2 = X[:, 1]
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)

        candidates = [
            ("sin(x1) + cos(x2)", s1 + c2, 2, 1),
            ("sin(x1) - cos(x2)", s1 - c2, 2, 1),
            ("sin(x1)", s1, 1, 0),
            ("cos(x2)", c2, 1, 0),
            ("sin(x1) + sin(x2)", s1 + s2, 2, 1),
            ("cos(x1) + cos(x2)", c1 + c2, 2, 1),
            ("sin(x1)*cos(x2)", s1 * c2, 2, 1),
            ("sin(x1)*sin(x2)", s1 * s2, 2, 1),
            ("cos(x1)*cos(x2)", c1 * c2, 2, 1),
            ("cos(x1) - sin(x2)", c1 - s2, 2, 1),
        ]

        best_expr = None
        best_pred = None
        best_mse = np.inf
        # prefer lower complexity: complexity metric = 2*bin + unary
        best_complexity = None

        for expr, pred, unary_ct, bin_ct in candidates:
            mse = self._mse(y, pred)
            complexity = 2 * bin_ct + unary_ct
            if mse < best_mse - 1e-14:
                best_mse = mse
                best_expr = expr
                best_pred = pred
                best_complexity = complexity
            elif abs(mse - best_mse) <= 1e-14:
                if complexity < (best_complexity if best_complexity is not None else 1e9):
                    best_mse = mse
                    best_expr = expr
                    best_pred = pred
                    best_complexity = complexity

        if best_expr is None:
            # Fallback to zero
            best_expr = "0"
            best_pred = np.zeros_like(y)
        return best_expr, best_pred
