import numpy as np
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        self.max_features_omp = kwargs.get("max_features_omp", 6)
        self.improvement_tol = kwargs.get("improvement_tol", 1e-6)
        self.coef_rel_threshold = kwargs.get("coef_rel_threshold", 1e-6)
        self.random_state = kwargs.get("random_state", 42)

    def _build_feature_library(self, x1, x2):
        # Base trigonometric features
        s1 = np.sin(x1); c1 = np.cos(x1)
        s2 = np.sin(x2); c2 = np.cos(x2)
        ssum = np.sin(x1 + x2); csum = np.cos(x1 + x2)
        sdiff = np.sin(x1 - x2); cdiff = np.cos(x1 - x2)
        s1c2 = s1 * c2; c1s2 = c1 * s2; s1s2 = s1 * s2; c1c2 = c1 * c2
        s2x1 = np.sin(2 * x1); c2x1 = np.cos(2 * x1)
        s2x2 = np.sin(2 * x2); c2x2 = np.cos(2 * x2)

        features = {
            "x1": x1,
            "x2": x2,
            "sin(x1)": s1,
            "cos(x1)": c1,
            "sin(x2)": s2,
            "cos(x2)": c2,
            "sin(x1+x2)": ssum,
            "cos(x1+x2)": csum,
            "sin(x1-x2)": sdiff,
            "cos(x1-x2)": cdiff,
            "sin(x1)*cos(x2)": s1c2,
            "cos(x1)*sin(x2)": c1s2,
            "sin(x1)*sin(x2)": s1s2,
            "cos(x1)*cos(x2)": c1c2,
            "sin(2*x1)": s2x1,
            "cos(2*x1)": c2x1,
            "sin(2*x2)": s2x2,
            "cos(2*x2)": c2x2,
        }
        return features

    def _candidate_feature_sets(self):
        # Curated sets likely to capture common SinCos relationships
        return [
            ["sin(x1)"],
            ["cos(x1)"],
            ["sin(x2)"],
            ["cos(x2)"],
            ["sin(x1)", "cos(x1)"],
            ["sin(x2)", "cos(x2)"],
            ["sin(x1)", "sin(x2)"],
            ["sin(x1)", "cos(x2)"],
            ["cos(x1)", "sin(x2)"],
            ["cos(x1)", "cos(x2)"],
            ["sin(x1)*cos(x2)"],
            ["cos(x1)*sin(x2)"],
            ["sin(x1)*sin(x2)"],
            ["cos(x1)*cos(x2)"],
            ["sin(x1+x2)"],
            ["cos(x1+x2)"],
            ["sin(x1-x2)"],
            ["cos(x1-x2)"],
            ["sin(2*x1)"],
            ["cos(2*x1)"],
            ["sin(2*x2)"],
            ["cos(2*x2)"],
            ["sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)"],
            ["x1"],
            ["x2"],
            ["x1", "x2"],
        ]

    def _lstsq_fit(self, features_arrays, y):
        # Solve least squares with intercept
        n = y.shape[0]
        if len(features_arrays) > 0:
            A = np.column_stack(features_arrays + [np.ones(n)])
        else:
            A = np.ones((n, 1))
        coefs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        if len(features_arrays) > 0:
            w = coefs[:-1]
            b = coefs[-1]
        else:
            w = np.array([])
            b = coefs[0]
        yhat = A @ coefs
        return w, b, yhat

    def _format_expression(self, coeffs, intercept, term_names, term_arrays, y):
        # Remove negligible terms
        y_rms = float(np.sqrt(np.mean(y**2)) + 1e-12)
        keep_indices = []
        for i, (a, arr) in enumerate(zip(coeffs, term_arrays)):
            arr_rms = float(np.sqrt(np.mean(arr**2)) + 1e-15)
            if abs(a) * arr_rms >= self.coef_rel_threshold * y_rms:
                keep_indices.append(i)
        coeffs = np.array([coeffs[i] for i in keep_indices], dtype=float) if len(keep_indices) > 0 else np.array([], dtype=float)
        term_names = [term_names[i] for i in keep_indices]
        term_arrays = [term_arrays[i] for i in keep_indices]

        # Threshold intercept
        if abs(intercept) < self.coef_rel_threshold * y_rms:
            intercept = 0.0

        # Build expression string
        tol1 = 1e-8
        parts = []
        # Terms
        for a, name in zip(coeffs, term_names):
            if abs(a) < 1e-15:
                continue
            sign = "-" if a < 0 else "+"
            aval = abs(a)
            if abs(aval - 1.0) <= tol1:
                piece = name
            else:
                piece = f"{aval:.10g}*{name}"
            if not parts:
                if sign == "-":
                    parts.append(f"-{piece}")
                else:
                    parts.append(piece)
            else:
                parts.append(f" {sign} {piece}")
        # Intercept
        if intercept != 0.0 or not parts:
            c = f"{intercept:.10g}"
            if not parts:
                parts.append(c)
            else:
                if intercept < 0:
                    parts.append(f" - {abs(intercept):.10g}")
                else:
                    parts.append(f" + {intercept:.10g}")

        expression = "".join(parts)
        # Compute predictions consistent with formatting
        if len(term_arrays) > 0:
            preds = np.sum(coeffs[:, None] * np.vstack([arr for arr in term_arrays]), axis=0) + intercept
        else:
            preds = np.full_like(y, fill_value=intercept, dtype=float)
        return expression, preds

    def _evaluate_candidate_set(self, feature_dict, keys, y):
        arrays = [feature_dict[k] for k in keys]
        w, b, yhat = self._lstsq_fit(arrays, y)
        expr, preds = self._format_expression(w, b, keys, arrays, y)
        mse = float(np.mean((y - preds)**2))
        comp = self._compute_complexity(expr)
        return {"expression": expr, "predictions": preds, "mse": mse, "complexity": comp, "terms": len(keys)}

    def _run_omp(self, feature_dict, y, max_features):
        # Orthogonal Matching Pursuit with intercept
        keys = list(feature_dict.keys())
        A = np.column_stack([feature_dict[k] for k in keys])  # n x m
        n, m = A.shape
        # Normalize columns for selection step
        col_rms = np.sqrt(np.mean(A**2, axis=0)) + 1e-15
        A_norm = A / col_rms

        selected = []
        residual = y.copy()
        prev_mse = float(np.mean((y - np.mean(y))**2))
        for _ in range(max_features):
            # Compute correlations
            unused = [j for j in range(m) if j not in selected]
            if not unused:
                break
            corrs = A_norm[:, unused].T @ residual  # shape len(unused,)
            jmax_rel = int(np.argmax(np.abs(corrs)))
            jmax = unused[jmax_rel]
            # If correlation is negligible, stop
            if abs(corrs[jmax_rel]) < 1e-12:
                break
            selected.append(jmax)
            # Fit with selected features (original scaling), including intercept
            arrays = [A[:, j] for j in selected]
            w, b, yhat = self._lstsq_fit(arrays, y)
            residual = y - yhat
            mse = float(np.mean(residual**2))
            if prev_mse - mse < self.improvement_tol * (np.var(y) + 1e-12):
                break
            prev_mse = mse

        sel_keys = [keys[j] for j in selected]
        arrays = [feature_dict[k] for k in sel_keys]
        w, b, yhat = self._lstsq_fit(arrays, y)
        expr, preds = self._format_expression(w, b, sel_keys, arrays, y)
        mse = float(np.mean((y - preds)**2))
        comp = self._compute_complexity(expr)
        return {"expression": expr, "predictions": preds, "mse": mse, "complexity": comp, "terms": len(sel_keys)}

    def _compute_complexity(self, expression):
        try:
            x1, x2 = sp.symbols('x1 x2')
            expr = sp.sympify(expression, locals={'sin': sp.sin, 'cos': sp.cos, 'exp': sp.exp, 'log': sp.log})
        except Exception:
            return None

        binary_ops = 0
        unary_ops = 0

        def visit(node):
            nonlocal binary_ops, unary_ops
            if isinstance(node, sp.Add):
                # n-1 additions
                binary_ops += max(len(node.args) - 1, 0)
                for a in node.args:
                    visit(a)
            elif isinstance(node, sp.Mul):
                # n-1 multiplications
                binary_ops += max(len(node.args) - 1, 0)
                for a in node.args:
                    visit(a)
            elif isinstance(node, sp.Pow):
                binary_ops += 1
                for a in node.args:
                    visit(a)
            elif isinstance(node, sp.Function):
                if node.func in [sp.sin, sp.cos, sp.exp, sp.log]:
                    unary_ops += 1
                for a in node.args:
                    visit(a)
            elif isinstance(node, (sp.Symbol, sp.Number, sp.Integer, sp.Float, sp.Rational)):
                return
            else:
                # generic
                for a in getattr(node, 'args', []):
                    visit(a)

        visit(expr)
        return 2 * binary_ops + unary_ops

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        if X.shape[1] != 2:
            raise ValueError("X must have exactly 2 columns: x1, x2")

        x1 = X[:, 0]
        x2 = X[:, 1]

        feature_dict = self._build_feature_library(x1, x2)

        results = []

        # Evaluate curated candidate sets
        for keys in self._candidate_feature_sets():
            res = self._evaluate_candidate_set(feature_dict, keys, y)
            results.append(res)

        # OMP result
        omp_res = self._run_omp(feature_dict, y, max_features=self.max_features_omp)
        results.append(omp_res)

        # Choose best by MSE, tie-break by complexity then by expression length
        best = None
        for r in results:
            if best is None:
                best = r
            else:
                if r["mse"] < best["mse"] - 1e-12:
                    best = r
                elif abs(r["mse"] - best["mse"]) <= 1e-12:
                    # tie-break by complexity if available
                    c1 = r.get("complexity", None)
                    c2 = best.get("complexity", None)
                    if c1 is not None and c2 is not None:
                        if c1 < c2:
                            best = r
                        elif c1 == c2 and len(r["expression"]) < len(best["expression"]):
                            best = r
                    else:
                        if len(r["expression"]) < len(best["expression"]):
                            best = r

        expression = best["expression"]
        predictions = best["predictions"]

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": best.get("complexity", None)}
        }