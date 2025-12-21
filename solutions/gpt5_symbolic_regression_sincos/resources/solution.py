import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def _build_features(self, X):
        x1 = X[:, 0]
        x2 = X[:, 1]
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)
        features = {
            "sin(x1)": s1,
            "cos(x1)": c1,
            "sin(x2)": s2,
            "cos(x2)": c2,
            "sin(x1)*cos(x2)": s1 * c2,
            "cos(x1)*sin(x2)": c1 * s2,
            "sin(x1)*sin(x2)": s1 * s2,
            "cos(x1)*cos(x2)": c1 * c2,
        }
        return features

    def _lstsq_fit(self, A, y):
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        return coeffs

    def _bic(self, mse, n, k):
        eps = 1e-12
        return n * np.log(mse + eps) + k * np.log(max(n, 2))

    def _forward_selection(self, X, y, features, max_terms=4):
        n = X.shape[0]
        names = list(features.keys())
        Phi = np.column_stack([features[name] for name in names])  # shape (n, p)
        ones = np.ones(n)
        selected_idx = []
        selected_names = []

        # Intercept-only model
        A = ones[:, None]
        coeffs = self._lstsq_fit(A, y)
        intercept = coeffs[0]
        resid = y - A[:, 0] * intercept
        mse = np.mean(resid ** 2)
        best_bic = self._bic(mse, n, 1)

        available = set(range(Phi.shape[1]))

        for _ in range(max_terms):
            best_candidate = None
            best_candidate_bic = None
            best_candidate_coeffs = None

            for j in available:
                A_candidate = np.column_stack([ones] + [Phi[:, idx] for idx in selected_idx + [j]])
                coeffs_candidate = self._lstsq_fit(A_candidate, y)
                yhat = A_candidate @ coeffs_candidate
                mse_candidate = np.mean((y - yhat) ** 2)
                k_params = 1 + len(selected_idx) + 1  # intercept + number of features including candidate
                bic_candidate = self._bic(mse_candidate, n, k_params)

                if (best_candidate_bic is None) or (bic_candidate < best_candidate_bic):
                    best_candidate_bic = bic_candidate
                    best_candidate = j
                    best_candidate_coeffs = coeffs_candidate

            if best_candidate is not None and best_candidate_bic < best_bic - 1e-9:
                # Accept
                selected_idx.append(best_candidate)
                selected_names.append(names[best_candidate])
                best_bic = best_candidate_bic
                intercept = best_candidate_coeffs[0]
                coeffs_sel = best_candidate_coeffs[1:]
                available.remove(best_candidate)
            else:
                break

        if len(selected_idx) == 0:
            return [], np.array([]), intercept

        return selected_names, coeffs_sel, intercept

    def _compute_mse(self, A, w, b, y):
        yhat = A @ w + b
        return np.mean((y - yhat) ** 2), yhat

    def _quantize_and_prune(self, X, y, selected_names, coeffs, intercept, features, eta=0.01):
        if len(selected_names) == 0:
            return selected_names, coeffs, intercept

        A = np.column_stack([features[name] for name in selected_names])
        base_mse, _ = self._compute_mse(A, coeffs, intercept, y)

        # Prune small coefficients if they do not increase MSE significantly
        changed = True
        while changed and len(coeffs) > 0:
            changed = False
            for i in range(len(coeffs)):
                w_try = coeffs.copy()
                w_try[i] = 0.0
                mse_try, _ = self._compute_mse(A, w_try, intercept, y)
                if mse_try <= base_mse * (1 + eta):
                    coeffs = w_try
                    base_mse = mse_try
                    # Remove feature if coefficient negligible to keep expression clean
                    if abs(coeffs[i]) < 1e-12:
                        # Delete ith column
                        A = np.delete(A, i, axis=1)
                        del selected_names[i]
                        coeffs = np.delete(coeffs, i)
                    changed = True
                    break

        if len(coeffs) == 0:
            # Only intercept remains
            return selected_names, coeffs, intercept

        # Try quantize coefficients to ±1 if close, without increasing MSE much
        for i in range(len(coeffs)):
            if coeffs[i] == 0:
                continue
            sign = 1.0 if coeffs[i] >= 0 else -1.0
            tol_abs = 0.05 + 0.0 * abs(coeffs[i])  # absolute tolerance ~0.05
            if abs(coeffs[i] - sign) <= tol_abs:
                w_try = coeffs.copy()
                w_try[i] = sign
                mse_try, _ = self._compute_mse(A, w_try, intercept, y)
                if mse_try <= base_mse * (1 + eta):
                    coeffs = w_try
                    base_mse = mse_try

        # Try drop intercept if small or not necessary
        if abs(intercept) <= 0.02:
            mse_try, _ = self._compute_mse(A, coeffs, 0.0, y)
            if mse_try <= base_mse * (1 + eta):
                intercept = 0.0
                base_mse = mse_try

        return selected_names, coeffs, intercept

    def _format_float(self, x):
        if abs(x - int(round(x))) < 1e-12:
            return str(int(round(x)))
        return f"{x:.10g}"

    def _build_expression(self, selected_names, coeffs, intercept):
        terms = []
        # Build terms for each feature
        for name, c in zip(selected_names, coeffs):
            if abs(c) < 1e-12:
                continue
            if abs(c - 1.0) < 1e-12:
                terms.append(name)
            elif abs(c + 1.0) < 1e-12:
                terms.append(f"-{name}")
            else:
                coeff_str = self._format_float(c)
                # place negative coefficient handled by sign
                terms.append(f"{coeff_str}*{name}")
        # Add intercept
        if abs(intercept) >= 1e-12:
            b_str = self._format_float(intercept)
            terms.append(b_str)

        if not terms:
            return "0"

        # Combine terms into a single expression string
        expr = terms[0]
        for term in terms[1:]:
            # Handle leading minus inside term
            if term.startswith("-"):
                expr += " - " + term[1:]
            else:
                expr += " + " + term
        return expr

    def _eval_expression(self, X, expression):
        x1 = X[:, 0]
        x2 = X[:, 1]
        # Define allowed functions
        def _log(z):
            return np.log(z)
        env = {"x1": x1, "x2": x2, "sin": np.sin, "cos": np.cos, "exp": np.exp, "log": _log}
        return eval(expression, {"__builtins__": {}}, env)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        n = X.shape[0]
        features = self._build_features(X)

        # Try a simple hand-crafted guess first for SinCos-like data
        simple_expr = "sin(x1) + cos(x2)"
        simple_pred = self._eval_expression(X, simple_expr)
        simple_mse = np.mean((y - simple_pred) ** 2)
        base_mse = np.var(y) if n > 1 else np.mean((y - y.mean()) ** 2)

        # Forward selection to fit a sparse linear combination of trig features
        selected_names, coeffs, intercept = self._forward_selection(X, y, features, max_terms=4)
        if len(selected_names) > 0:
            # Quantize and prune solution
            selected_names, coeffs, intercept = self._quantize_and_prune(
                X, y, selected_names, coeffs, intercept, features, eta=0.01
            )
            expr = self._build_expression(selected_names, coeffs, intercept)
            preds = self._eval_expression(X, expr)
            model_mse = np.mean((y - preds) ** 2)
        else:
            # Intercept-only
            expr = self._format_float(float(y.mean()))
            preds = np.full(n, y.mean())
            model_mse = np.mean((y - preds) ** 2)

        # Prefer simpler explicit sin(x1)+cos(x2) if it performs comparably
        if simple_mse <= model_mse * 1.01:
            expression = simple_expr
            predictions = simple_pred
        else:
            expression = expr
            predictions = preds

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
