import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def _format_float(self, x):
        if not np.isfinite(x):
            return "0"
        # Use 12 significant digits for stability while keeping expression concise
        s = f"{x:.12g}"
        # Ensure there's a decimal for integers to be explicit floats
        if "." not in s and "e" not in s and "E" not in s:
            s += ".0"
        return s

    def _build_expression(self, intercept, feature_names, coefs, tol=0.0):
        # Construct expression string from intercept and feature terms with coefficients
        expr = ""
        # Add intercept if significant
        if abs(intercept) > tol:
            expr = self._format_float(intercept)

        # Build terms with correct signs and minimal parentheses
        for name, c in zip(feature_names, coefs):
            if abs(c) <= tol:
                continue
            sign = 1.0 if c >= 0 else -1.0
            ac = abs(c)
            # Avoid writing 1*term
            if np.isclose(ac, 1.0, rtol=1e-9, atol=1e-12):
                term_str = name
            else:
                term_str = f"{self._format_float(ac)}*{name}"

            if expr == "":
                # First term
                if sign < 0:
                    expr = f"-{term_str}" if np.isclose(ac, 1.0, rtol=1e-9, atol=1e-12) else f"-{term_str}"
                else:
                    expr = term_str
            else:
                if sign < 0:
                    expr = f"{expr} - {term_str}"
                else:
                    expr = f"{expr} + {term_str}"

        if expr == "":
            expr = "0.0"
        return expr

    def _fit_with_features(self, y, feature_arrays, tol):
        # feature_arrays: list of np arrays (n,)
        n = y.shape[0]
        k = len(feature_arrays)
        if k == 0:
            # Constant model
            intercept = float(np.mean(y))
            yhat = np.full_like(y, intercept)
            mse = float(np.mean((y - yhat) ** 2))
            return intercept, np.array([]), yhat, mse

        A = np.column_stack(feature_arrays + [np.ones(n)])
        # Solve least squares
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        feat_coefs = coeffs[:-1]
        intercept = float(coeffs[-1])

        # Prune small coefficients and refit
        keep_idx = [i for i, c in enumerate(feat_coefs) if abs(c) > tol]
        if len(keep_idx) != k:
            if len(keep_idx) == 0:
                A2 = np.ones((n, 1))
            else:
                A2 = np.column_stack([feature_arrays[i] for i in keep_idx] + [np.ones(n)])
            coeffs2, _, _, _ = np.linalg.lstsq(A2, y, rcond=None)
            feat_coefs2 = np.zeros_like(feat_coefs)
            if len(keep_idx) > 0:
                feat_coefs2[keep_idx] = coeffs2[:-1]
            intercept = float(coeffs2[-1])
            feat_coefs = feat_coefs2

        yhat = A @ np.append(feat_coefs, intercept)
        mse = float(np.mean((y - yhat) ** 2))
        return intercept, feat_coefs, yhat, mse

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        n = X.shape[0]
        if X.shape[1] != 2:
            raise ValueError("Expected X with shape (n, 2).")

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Precompute basic trigonometric features
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)

        # Pairwise products
        s1c2 = s1 * c2
        c1s2 = c1 * s2
        s1s2 = s1 * s2
        c1c2 = c1 * c2

        # Sum/difference trig
        s_sum = np.sin(x1 + x2)
        c_sum = np.cos(x1 + x2)
        s_diff = np.sin(x1 - x2)
        c_diff = np.cos(x1 - x2)

        # Mapping from feature names to arrays
        values_map = {
            "sin(x1)": s1,
            "cos(x1)": c1,
            "sin(x2)": s2,
            "cos(x2)": c2,
            "sin(x1)*cos(x2)": s1c2,
            "cos(x1)*sin(x2)": c1s2,
            "sin(x1)*sin(x2)": s1s2,
            "cos(x1)*cos(x2)": c1c2,
            "sin(x1 + x2)": s_sum,
            "cos(x1 + x2)": c_sum,
            "sin(x1 - x2)": s_diff,
            "cos(x1 - x2)": c_diff,
        }

        # Candidate feature sets (each implicitly includes an intercept)
        candidate_sets = [
            ["sin(x1)", "cos(x2)"],
            ["sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)"],
            ["sin(x1)*cos(x2)"],
            ["sin(x1)*cos(x2)", "cos(x1)*sin(x2)"],
            ["sin(x1)*sin(x2)"],
            ["cos(x1)*cos(x2)"],
            ["sin(x1)*sin(x2)", "cos(x1)*cos(x2)"],
            ["sin(x1 + x2)"],
            ["cos(x1 + x2)"],
            ["sin(x1 - x2)"],
            ["cos(x1 - x2)"],
            ["sin(x1 + x2)", "cos(x1 - x2)"],
            ["sin(x1)", "cos(x2)", "sin(x1)*cos(x2)"],
            ["sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)", "sin(x1)*cos(x2)"],
            ["sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)", "sin(x1)*cos(x2)", "cos(x1)*sin(x2)"],
            ["sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)", "sin(x1)*sin(x2)", "cos(x1)*cos(x2)"],
            ["sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)", "sin(x1)*sin(x2)", "sin(x1)*cos(x2)", "cos(x1)*sin(x2)", "cos(x1)*cos(x2)"],
            ["sin(x1 + x2)", "sin(x1 - x2)", "cos(x1 + x2)", "cos(x1 - x2)"],
        ]

        sigma = float(np.std(y))
        tol = max(1e-9, 1e-6 * (sigma if sigma > 0 else 1.0))

        best = {
            "mse": np.inf,
            "expr": None,
            "yhat": None,
            "intercept": None,
            "feature_names": None,
            "coefs": None,
        }

        # Evaluate candidate sets
        for names in candidate_sets:
            feature_arrays = [values_map[n] for n in names]
            intercept, coefs, yhat, mse = self._fit_with_features(y, feature_arrays, tol)
            # Compute simplified list after pruning
            kept_names = [n for n, c in zip(names, coefs) if abs(c) > tol]
            kept_coefs = [c for c in coefs if abs(c) > tol]
            expr = self._build_expression(intercept if abs(intercept) > tol else 0.0, kept_names, kept_coefs, tol)

            # Tie-breaking: prefer fewer terms, then shorter expression string
            terms_count = len(kept_coefs) + (1 if abs(intercept) > tol else 0)
            if best["expr"] is None:
                accept = True
            else:
                if mse + 1e-14 < best["mse"]:
                    accept = True
                elif abs(mse - best["mse"]) <= max(1e-12, 1e-12 * (1.0 + best["mse"])):
                    # Tie: prefer fewer terms
                    prev_terms = len(best["feature_names"]) + (1 if abs(best["intercept"]) > tol else 0)
                    if terms_count < prev_terms:
                        accept = True
                    elif terms_count == prev_terms and len(expr) < len(best["expr"]):
                        accept = True
                    else:
                        accept = False
                else:
                    accept = False

            if accept:
                best["mse"] = mse
                best["expr"] = expr
                best["yhat"] = yhat
                best["intercept"] = intercept
                best["feature_names"] = kept_names
                best["coefs"] = kept_coefs

        # Final fallback if nothing selected
        if best["expr"] is None:
            intercept = float(np.mean(y))
            expr = self._format_float(intercept)
            yhat = np.full_like(y, intercept)
            best["expr"] = expr
            best["yhat"] = yhat

        return {
            "expression": best["expr"],
            "predictions": best["yhat"].tolist(),
            "details": {}
        }
