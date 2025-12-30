import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.round_decimals = int(kwargs.get("round_decimals", 8))
        self.max_terms_omp = int(kwargs.get("max_terms_omp", 5))
        self.mse_tie_rel_margin = float(kwargs.get("mse_tie_rel_margin", 0.005))
        self.zero_tol = float(kwargs.get("zero_tol", 1e-12))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0]
        x2 = X[:, 1]
        n = X.shape[0]

        # Precompute basic trig features
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)

        s12 = np.sin(x1 + x2)
        s1m2 = np.sin(x1 - x2)
        c12 = np.cos(x1 + x2)
        c1m2 = np.cos(x1 - x2)

        s2x1 = np.sin(2 * x1)
        c2x1 = np.cos(2 * x1)
        s2x2 = np.sin(2 * x2)
        c2x2 = np.cos(2 * x2)

        s1c2 = s1 * c2
        c1s2 = c1 * s2
        s1s2 = s1 * s2
        c1c2 = c1 * c2

        ones = np.ones(n, dtype=float)

        # Feature metadata: unary ops and internal binary ops inside the feature string
        feat_meta = {
            "1": (0, 0),
            "x1": (0, 0),
            "x2": (0, 0),
            "sin(x1)": (1, 0),
            "cos(x1)": (1, 0),
            "sin(x2)": (1, 0),
            "cos(x2)": (1, 0),
            "sin(x1 + x2)": (1, 1),
            "sin(x1 - x2)": (1, 1),
            "cos(x1 + x2)": (1, 1),
            "cos(x1 - x2)": (1, 1),
            "sin(2*x1)": (1, 1),
            "cos(2*x1)": (1, 1),
            "sin(2*x2)": (1, 1),
            "cos(2*x2)": (1, 1),
            "sin(x1)*cos(x2)": (2, 1),
            "cos(x1)*sin(x2)": (2, 1),
            "sin(x1)*sin(x2)": (2, 1),
            "cos(x1)*cos(x2)": (2, 1),
        }

        # Helper to compute MSE
        def mse(y_true, y_pred):
            r = y_true - y_pred
            return float(np.mean(r * r))

        # Helper to format coefficient with rounding
        def round_coef(c):
            return float(np.round(c, self.round_decimals))

        # Build expression string and compute complexity from basis and rounded coefficients
        def build_expression_and_complexity(terms, coeffs):
            # terms: list of feature string names (e.g., "sin(x1)")
            # coeffs: list/array of floats aligned with terms
            nonconst_parts = []
            const_val = 0.0
            unary_ops = 0
            bin_ops_inside_terms = 0
            mul_by_coef_count = 0

            for t, c in zip(terms, coeffs):
                if abs(c) <= self.zero_tol:
                    continue
                if t == "1":
                    const_val += c
                    continue

                uc, bc = feat_meta.get(t, (0, 0))
                unary_ops += uc
                bin_ops_inside_terms += bc

                # Multiplication by coefficient unless coef == 1 exactly
                if abs(c - 1.0) <= self.zero_tol:
                    nonconst_parts.append(f"{t}")
                else:
                    # Always include multiplication; if coef negative, it's still a multiplication
                    coef_str = self._coef_to_str(c)
                    nonconst_parts.append(f"{coef_str}*{t}")
                    mul_by_coef_count += 1 if abs(c - 1.0) > self.zero_tol else 0

            expr_parts = list(nonconst_parts)
            if abs(const_val) > self.zero_tol:
                expr_parts.append(self._coef_to_str(const_val))

            if len(expr_parts) == 0:
                expression = "0"
                total_binary_ops = 0
            else:
                expression = " + ".join(expr_parts)
                # additions between parts
                additions_count = max(len(expr_parts) - 1, 0)
                total_binary_ops = additions_count + mul_by_coef_count + bin_ops_inside_terms

            complexity = int(2 * total_binary_ops + unary_ops)
            return expression, complexity

        # Solve least squares for given A and terms; returns expression, preds, mse, complexity
        def fit_candidate(A, terms):
            # Solve least squares
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            # Round coefficients to ensure expression matches predictions
            coeffs = np.array([round_coef(c) for c in coeffs], dtype=float)
            # Drop effectively zero terms for expression/complexity, but keep them zero in A @ coeffs obviously
            yhat = A @ coeffs
            candidate_mse = mse(y, yhat)
            expression, complexity = build_expression_and_complexity(terms, coeffs)
            return {
                "expression": expression,
                "predictions": yhat,
                "mse": candidate_mse,
                "complexity": complexity,
            }

        candidates = []

        # Simple parametric candidates
        # 1) a*sin(x1) + b*cos(x2) + c
        A = np.column_stack([s1, c2, ones])
        terms = ["sin(x1)", "cos(x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 2) a*sin(x1) + b*sin(x2) + c
        A = np.column_stack([s1, s2, ones])
        terms = ["sin(x1)", "sin(x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 3) a*cos(x1) + b*cos(x2) + c
        A = np.column_stack([c1, c2, ones])
        terms = ["cos(x1)", "cos(x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 4) General sum of sin and cos for each variable + intercept
        A = np.column_stack([s1, c1, s2, c2, ones])
        terms = ["sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 5) a*sin(x1 + x2) + b
        A = np.column_stack([s12, ones])
        terms = ["sin(x1 + x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 6) a*sin(x1 - x2) + b
        A = np.column_stack([s1m2, ones])
        terms = ["sin(x1 - x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 7) a*cos(x1 + x2) + b
        A = np.column_stack([c12, ones])
        terms = ["cos(x1 + x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 8) a*cos(x1 - x2) + b
        A = np.column_stack([c1m2, ones])
        terms = ["cos(x1 - x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 9) a*sin(x1)*cos(x2) + b
        A = np.column_stack([s1c2, ones])
        terms = ["sin(x1)*cos(x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 10) a*sin(x1)*cos(x2) + b*cos(x1)*sin(x2) + c
        A = np.column_stack([s1c2, c1s2, ones])
        terms = ["sin(x1)*cos(x2)", "cos(x1)*sin(x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 11) Linear baseline a*x1 + b*x2 + c
        A = np.column_stack([x1, x2, ones])
        terms = ["x1", "x2", "1"]
        candidates.append(fit_candidate(A, terms))

        # 12) Enriched harmonics a*sin(2*x1)+b*cos(2*x1)+c*sin(2*x2)+d*cos(2*x2)+e
        A = np.column_stack([s2x1, c2x1, s2x2, c2x2, ones])
        terms = ["sin(2*x1)", "cos(2*x1)", "sin(2*x2)", "cos(2*x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # 13) Products of sines and cosines + intercept
        A = np.column_stack([s1s2, c1c2, s1c2, c1s2, ones])
        terms = ["sin(x1)*sin(x2)", "cos(x1)*cos(x2)", "sin(x1)*cos(x2)", "cos(x1)*sin(x2)", "1"]
        candidates.append(fit_candidate(A, terms))

        # OMP over a dictionary of features
        dict_features = [
            (ones, "1"),
            (x1, "x1"),
            (x2, "x2"),
            (s1, "sin(x1)"),
            (c1, "cos(x1)"),
            (s2, "sin(x2)"),
            (c2, "cos(x2)"),
            (s12, "sin(x1 + x2)"),
            (s1m2, "sin(x1 - x2)"),
            (c12, "cos(x1 + x2)"),
            (c1m2, "cos(x1 - x2)"),
            (s2x1, "sin(2*x1)"),
            (c2x1, "cos(2*x1)"),
            (s2x2, "sin(2*x2)"),
            (c2x2, "cos(2*x2)"),
            (s1s2, "sin(x1)*sin(x2)"),
            (c1c2, "cos(x1)*cos(x2)"),
            (s1c2, "sin(x1)*cos(x2)"),
            (c1s2, "cos(x1)*sin(x2)"),
        ]

        omp_result = self._omp_fit(y, dict_features)
        if omp_result is not None:
            candidates.append(omp_result)

        # Choose best candidate by MSE, with tie-break towards lower complexity
        best = self._select_best_candidate(candidates)

        return {
            "expression": best["expression"],
            "predictions": best["predictions"].tolist(),
            "details": {"complexity": best["complexity"]},
        }

    def _coef_to_str(self, c):
        # Ensure stable numeric string for coefficients
        if np.isfinite(c):
            # Represent with fixed rounding
            cr = float(np.round(c, self.round_decimals))
            return repr(cr)
        else:
            return "0.0"

    def _select_best_candidate(self, candidates):
        # Primary: lowest MSE; Secondary: lower complexity if within relative margin
        best = None
        for cand in candidates:
            if best is None:
                best = cand
                continue
            if cand["mse"] < best["mse"]:
                best = cand
            elif best["mse"] > 0:
                rel = (cand["mse"] - best["mse"]) / max(best["mse"], 1e-15)
                if rel <= self.mse_tie_rel_margin:
                    if cand["complexity"] < best["complexity"]:
                        best = cand
        return best

    def _omp_fit(self, y, dict_features):
        # Orthogonal Matching Pursuit with up to max_terms_omp terms
        # Build design matrix and normalize columns for selection metric
        # dict_features: list of (column_vector, feature_name)
        n_feats = len(dict_features)
        n = dict_features[0][0].shape[0]
        A_full = np.zeros((n, n_feats), dtype=float)
        terms = []
        norms = np.zeros(n_feats, dtype=float)
        for j, (col, name) in enumerate(dict_features):
            A_full[:, j] = col
            terms.append(name)
            norms[j] = np.linalg.norm(col)
        # Avoid division by zero
        norms = np.where(norms == 0, 1.0, norms)

        selected = []
        residual = y.copy()
        best_result = None

        for k in range(min(self.max_terms_omp, n_feats)):
            # Compute correlations
            remaining = [j for j in range(n_feats) if j not in selected]
            if not remaining:
                break
            corrs = np.array([abs(np.dot(A_full[:, j], residual)) / norms[j] for j in remaining])
            j_best = remaining[int(np.argmax(corrs))]
            selected.append(j_best)

            # Solve LS on selected set
            A_sel = A_full[:, selected]
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A_sel, y, rcond=None)
            except np.linalg.LinAlgError:
                break
            # Round coefficients
            coeffs = np.array([float(np.round(c, self.round_decimals)) for c in coeffs], dtype=float)
            yhat = A_sel @ coeffs
            current_mse = float(np.mean((y - yhat) ** 2))

            # Build expression and complexity
            expression, complexity = self._build_expr_from_selected(terms, selected, coeffs)

            result = {
                "expression": expression,
                "predictions": yhat,
                "mse": current_mse,
                "complexity": complexity,
            }

            if best_result is None:
                best_result = result
            else:
                if result["mse"] < best_result["mse"]:
                    best_result = result
                elif best_result["mse"] > 0:
                    rel = (result["mse"] - best_result["mse"]) / max(best_result["mse"], 1e-15)
                    if rel <= self.mse_tie_rel_margin and result["complexity"] < best_result["complexity"]:
                        best_result = result

            residual = y - yhat

            # Early stopping if very small residual
            if np.mean(residual ** 2) < 1e-14:
                break

        return best_result

    def _build_expr_from_selected(self, all_terms, selected_indices, coeffs):
        # all_terms: list of feature names aligned with columns
        # selected_indices: list of indices selected
        # coeffs: coefficients aligned with selected_indices
        # We'll reuse the complexity computation similar to build_expression_and_complexity
        feat_meta = {
            "1": (0, 0),
            "x1": (0, 0),
            "x2": (0, 0),
            "sin(x1)": (1, 0),
            "cos(x1)": (1, 0),
            "sin(x2)": (1, 0),
            "cos(x2)": (1, 0),
            "sin(x1 + x2)": (1, 1),
            "sin(x1 - x2)": (1, 1),
            "cos(x1 + x2)": (1, 1),
            "cos(x1 - x2)": (1, 1),
            "sin(2*x1)": (1, 1),
            "cos(2*x1)": (1, 1),
            "sin(2*x2)": (1, 1),
            "cos(2*x2)": (1, 1),
            "sin(x1)*cos(x2)": (2, 1),
            "cos(x1)*sin(x2)": (2, 1),
            "sin(x1)*sin(x2)": (2, 1),
            "cos(x1)*cos(x2)": (2, 1),
        }

        nonconst_parts = []
        const_val = 0.0
        unary_ops = 0
        bin_ops_inside_terms = 0
        mul_by_coef_count = 0

        for idx, c in zip(selected_indices, coeffs):
            name = all_terms[idx]
            if abs(c) <= self.zero_tol:
                continue
            if name == "1":
                const_val += c
                continue
            uc, bc = feat_meta.get(name, (0, 0))
            unary_ops += uc
            bin_ops_inside_terms += bc
            if abs(c - 1.0) <= self.zero_tol:
                nonconst_parts.append(f"{name}")
            else:
                coef_str = self._coef_to_str(c)
                nonconst_parts.append(f"{coef_str}*{name}")
                mul_by_coef_count += 1 if abs(c - 1.0) > self.zero_tol else 0

        expr_parts = list(nonconst_parts)
        if abs(const_val) > self.zero_tol:
            expr_parts.append(self._coef_to_str(const_val))

        if len(expr_parts) == 0:
            expression = "0"
            total_binary_ops = 0
        else:
            expression = " + ".join(expr_parts)
            additions_count = max(len(expr_parts) - 1, 0)
            total_binary_ops = additions_count + mul_by_coef_count + bin_ops_inside_terms

        complexity = int(2 * total_binary_ops + unary_ops)
        return expression, complexity