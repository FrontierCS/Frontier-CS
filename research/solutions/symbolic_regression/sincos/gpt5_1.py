import numpy as np

class Solution:
    def __init__(self, max_terms: int = 5, improvement_tol: float = 1e-8, **kwargs):
        self.max_terms = int(max_terms)
        self.improvement_tol = float(improvement_tol)

    def _build_feature_set(self, X):
        x1 = X[:, 0]
        x2 = X[:, 1]
        feats = []
        feats.append(("1", np.ones_like(x1)))
        feats.append(("sin(x1)", np.sin(x1)))
        feats.append(("cos(x1)", np.cos(x1)))
        feats.append(("sin(x2)", np.sin(x2)))
        feats.append(("cos(x2)", np.cos(x2)))
        feats.append(("sin(x1)*cos(x2)", np.sin(x1) * np.cos(x2)))
        feats.append(("cos(x1)*sin(x2)", np.cos(x1) * np.sin(x2)))
        feats.append(("sin(x1)*sin(x2)", np.sin(x1) * np.sin(x2)))
        feats.append(("cos(x1)*cos(x2)", np.cos(x1) * np.cos(x2)))
        feats.append(("sin(x1 + x2)", np.sin(x1 + x2)))
        feats.append(("cos(x1 + x2)", np.cos(x1 + x2)))
        feats.append(("sin(x1 - x2)", np.sin(x1 - x2)))
        feats.append(("cos(x1 - x2)", np.cos(x1 - x2)))
        feats.append(("sin(2*x1)", np.sin(2 * x1)))
        feats.append(("cos(2*x1)", np.cos(2 * x1)))
        feats.append(("sin(2*x2)", np.sin(2 * x2)))
        feats.append(("cos(2*x2)", np.cos(2 * x2)))
        return feats

    def _format_number(self, val):
        # Use a consistent concise float representation
        return f"{val:.12g}"

    def _build_expression(self, coeffs, term_names):
        # Build a clean expression string with proper signs
        pieces = []
        for c, t in zip(coeffs, term_names):
            if abs(c) < 1e-12:
                continue
            abs_c = abs(c)
            if t == "1":
                term_str = self._format_number(abs_c)
            else:
                term_str = f"{self._format_number(abs_c)}*{t}"
            sign = "-" if c < 0 else "+"
            pieces.append((sign, term_str))
        if not pieces:
            return "0"
        # Start with first piece, noting its sign
        first_sign, first_term = pieces[0]
        expr = first_term if first_sign == "+" else f"- {first_term}"
        for sign, term in pieces[1:]:
            if sign == "+":
                expr += f" + {term}"
            else:
                expr += f" - {term}"
        return expr

    def _fit_linear(self, A, y):
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        preds = A @ coeffs
        mse = float(np.mean((y - preds) ** 2))
        return coeffs, preds, mse

    def _evaluate_candidate(self, feature_map, terms, y):
        # terms: list of term names
        A_cols = [feature_map[t] for t in terms]
        A = np.column_stack(A_cols) if A_cols else np.zeros((y.shape[0], 0))
        coeffs, preds, mse = self._fit_linear(A, y)
        expr = self._build_expression(coeffs, terms)
        return expr, preds, mse, coeffs

    def _greedy_stepwise(self, feature_items, y):
        # feature_items: list of (name, values), include "1" as possible term
        n = y.shape[0]
        names = [nm for nm, _ in feature_items]
        values = [v for _, v in feature_items]
        name_to_idx = {nm: i for i, nm in enumerate(names)}

        selected = []
        # Start with constant term if available
        if "1" in name_to_idx:
            selected.append(name_to_idx["1"])

        def build_design_matrix(sel):
            if not sel:
                return np.zeros((n, 0))
            return np.column_stack([values[i] for i in sel])

        A = build_design_matrix(selected)
        coeffs, preds, best_mse = self._fit_linear(A, y)

        remaining = [i for i in range(len(names)) if i not in selected]
        max_additional = max(0, self.max_terms - (len(selected) - (1 if "1" in name_to_idx else 0)))

        # Tolerance scaled by data magnitude
        sse_tol = self.improvement_tol * n * np.var(y) if np.var(y) > 0 else self.improvement_tol

        for _ in range(max_additional):
            best_candidate = None
            best_candidate_mse = best_mse
            best_candidate_coeffs = None
            best_candidate_preds = None

            for j in remaining:
                Aj = np.column_stack([A, values[j]]) if A.size else values[j].reshape(-1, 1)
                c_j, p_j, mse_j = self._fit_linear(Aj, y)
                if mse_j < best_candidate_mse - (sse_tol / n):
                    best_candidate = j
                    best_candidate_mse = mse_j
                    best_candidate_coeffs = c_j
                    best_candidate_preds = p_j

            if best_candidate is None:
                break

            selected.append(best_candidate)
            remaining.remove(best_candidate)
            A = build_design_matrix(selected)
            coeffs = best_candidate_coeffs
            preds = best_candidate_preds
            best_mse = best_candidate_mse

        final_names = [names[i] for i in selected]
        expr = self._build_expression(coeffs, final_names)
        return expr, preds, best_mse, coeffs, final_names

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        features = self._build_feature_set(X)
        feature_map = {nm: v for nm, v in features}

        # Predefined candidate models (from simplest plausible forms)
        candidates = [
            ["sin(x1)", "cos(x2)", "1"],
            ["sin(x1)", "cos(x2)"],
            ["sin(x1 + x2)", "1"],
            ["cos(x1 + x2)", "1"],
            ["sin(x1)*cos(x2)", "1"],
            ["sin(x1)", "sin(x2)", "1"],
            ["cos(x1)", "cos(x2)", "1"],
            ["sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)", "1"],
        ]

        best_expr = None
        best_preds = None
        best_mse = float("inf")

        # Evaluate predefined candidates
        for terms in candidates:
            expr, preds, mse, _ = self._evaluate_candidate(feature_map, terms, y)
            if mse < best_mse:
                best_mse = mse
                best_expr = expr
                best_preds = preds

        # Greedy stepwise over broader dictionary
        expr_sw, preds_sw, mse_sw, _, _ = self._greedy_stepwise(features, y)
        if mse_sw < best_mse:
            best_expr = expr_sw
            best_preds = preds_sw
            best_mse = mse_sw

        return {
            "expression": best_expr,
            "predictions": best_preds.tolist(),
            "details": {}
        }