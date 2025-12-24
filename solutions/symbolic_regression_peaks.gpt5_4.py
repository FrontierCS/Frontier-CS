import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.max_terms = kwargs.get("max_terms", 3)
        self.random_state = kwargs.get("random_state", 42)

    def _format_float(self, x):
        if not np.isfinite(x):
            return "0"
        if abs(x) < 1e-15:
            return "0"
        return f"{float(x):.12g}"

    def _gaussian(self, x1, x2, cx, cy):
        return np.exp(-((x1 - cx) ** 2 + (x2 - cy) ** 2))

    def _build_library(self, X):
        x1 = X[:, 0]
        x2 = X[:, 1]

        def gexpr(cx, cy):
            return f"exp(-((x1 - ({self._format_float(cx)}))**2) - ((x2 - ({self._format_float(cy)}))**2))"

        features = []

        g00 = self._gaussian(x1, x2, 0.0, 0.0)
        g00_expr = gexpr(0.0, 0.0)

        g0m1 = self._gaussian(x1, x2, 0.0, -1.0)
        g0m1_expr = gexpr(0.0, -1.0)

        gm10 = self._gaussian(x1, x2, -1.0, 0.0)
        gm10_expr = gexpr(-1.0, 0.0)

        g10 = self._gaussian(x1, x2, 1.0, 0.0)
        g10_expr = gexpr(1.0, 0.0)

        g01 = self._gaussian(x1, x2, 0.0, 1.0)
        g01_expr = gexpr(0.0, 1.0)

        # Peaks-like core features
        f1_vals = ((1.0 - x1) ** 2) * g0m1
        f1_expr = f"((1 - x1)**2)*({g0m1_expr})"
        features.append({"expr": f1_expr, "values": f1_vals, "tag": "peaks_g1"})

        f2_vals = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * g00
        f2_expr = f"((x1/5 - x1**3 - x2**5))*({g00_expr})"
        features.append({"expr": f2_expr, "values": f2_vals, "tag": "peaks_g2"})

        f3_vals = gm10
        f3_expr = f"{gm10_expr}"
        features.append({"expr": f3_expr, "values": f3_vals, "tag": "peaks_g3"})

        # Additional Gaussian-only terms
        features.append({"expr": g0m1_expr, "values": g0m1, "tag": "g_0_-1"})
        features.append({"expr": g00_expr, "values": g00, "tag": "g_0_0"})
        features.append({"expr": g10_expr, "values": g10, "tag": "g_1_0"})
        features.append({"expr": g01_expr, "values": g01, "tag": "g_0_1"})

        # Gaussian-modulated polynomials around (0,0)
        features.append({"expr": f"(x1)*({g00_expr})", "values": x1 * g00, "tag": "x1_g00"})
        features.append({"expr": f"(x2)*({g00_expr})", "values": x2 * g00, "tag": "x2_g00"})
        features.append({"expr": f"(x1**2)*({g00_expr})", "values": (x1 ** 2) * g00, "tag": "x1^2_g00"})
        features.append({"expr": f"(x2**2)*({g00_expr})", "values": (x2 ** 2) * g00, "tag": "x2^2_g00"})
        features.append({"expr": f"(x1*x2)*({g00_expr})", "values": (x1 * x2) * g00, "tag": "x1x2_g00"})

        # Polynomial-only terms
        features.append({"expr": "x1", "values": x1, "tag": "x1"})
        features.append({"expr": "x2", "values": x2, "tag": "x2"})
        features.append({"expr": "x1**2", "values": x1 ** 2, "tag": "x1^2"})
        features.append({"expr": "x2**2", "values": x2 ** 2, "tag": "x2^2"})
        features.append({"expr": "x1*x2", "values": x1 * x2, "tag": "x1x2"})
        features.append({"expr": "x1**3", "values": x1 ** 3, "tag": "x1^3"})
        features.append({"expr": "x2**3", "values": x2 ** 3, "tag": "x2^3"})

        return features

    def _lstsq_fit(self, A, y):
        coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        y_pred = A @ coef
        mse = float(np.mean((y - y_pred) ** 2))
        return coef, y_pred, mse

    def _forward_selection(self, features, y, max_terms):
        n = y.shape[0]
        ones = np.ones(n)
        selected = []
        selected_idxs = []
        current_A = ones.reshape(-1, 1)
        current_coef, current_pred, current_mse = self._lstsq_fit(current_A, y)

        remaining = list(range(len(features)))
        tol = 1e-12

        for _ in range(max_terms):
            best_idx = None
            best_mse = current_mse
            best_coef = None
            best_A = None
            for idx in remaining:
                cand_col = features[idx]["values"].reshape(-1, 1)
                A = np.column_stack([current_A, cand_col])
                coef, pred, mse = self._lstsq_fit(A, y)
                if mse + 1e-16 < best_mse:
                    best_mse = mse
                    best_idx = idx
                    best_coef = coef
                    best_A = A
            if best_idx is None or (current_mse - best_mse) <= max(tol, 1e-9 * (1.0 + current_mse)):
                break
            # Accept best
            selected.append(features[best_idx])
            selected_idxs.append(best_idx)
            current_A = best_A
            current_coef = best_coef
            current_mse = best_mse
            remaining.remove(best_idx)

        return selected_idxs, current_coef, current_A, current_mse

    def _build_expression(self, intercept, coeffs, terms_exprs):
        parts = []
        parts.append(self._format_float(intercept))
        for c, expr in zip(coeffs, terms_exprs):
            if abs(c) < 1e-15:
                continue
            c_str = self._format_float(abs(c))
            if c >= 0:
                parts.append(f"+ ({c_str})*({expr})")
            else:
                parts.append(f"- ({c_str})*({expr})")
        return " ".join(parts)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).ravel()
        n = y.shape[0]
        if X.shape[1] != 2:
            raise ValueError("Input X must have exactly 2 columns for x1 and x2.")

        rng = np.random.default_rng(self.random_state)

        # Build feature library
        features = self._build_library(X)

        # Identify indices for peaks triple
        peaks_indices = {}
        for i, f in enumerate(features):
            if f.get("tag") == "peaks_g1":
                peaks_indices["g1"] = i
            elif f.get("tag") == "peaks_g2":
                peaks_indices["g2"] = i
            elif f.get("tag") == "peaks_g3":
                peaks_indices["g3"] = i

        ones = np.ones(n)

        # Fit peaks triple + intercept if available
        mse_peaks = np.inf
        expr_peaks = None
        pred_peaks = None

        if {"g1", "g2", "g3"}.issubset(peaks_indices.keys()):
            A_peaks = np.column_stack([
                ones,
                features[peaks_indices["g1"]]["values"],
                features[peaks_indices["g2"]]["values"],
                features[peaks_indices["g3"]]["values"],
            ])
            coef_peaks, pred_p, mse_p = self._lstsq_fit(A_peaks, y)
            b0 = coef_peaks[0]
            c1, c2, c3 = coef_peaks[1:]
            expr_peaks = self._build_expression(
                b0,
                [c1, c2, c3],
                [
                    features[peaks_indices["g1"]]["expr"],
                    features[peaks_indices["g2"]]["expr"],
                    features[peaks_indices["g3"]]["expr"],
                ],
            )
            mse_peaks = mse_p
            pred_peaks = pred_p

        # Forward selection from library
        max_terms = max(1, int(self.max_terms))
        sel_idxs, sel_coef, sel_A, mse_fs = self._forward_selection(features, y, max_terms)
        intercept_fs = sel_coef[0]
        coefs_fs = sel_coef[1:]
        exprs_fs = [features[idx]["expr"] for idx in sel_idxs]
        expr_fs = self._build_expression(intercept_fs, coefs_fs, exprs_fs)
        preds_fs = sel_A @ sel_coef

        # Choose between peaks triple and forward selection
        # Prefer simpler peaks if it is close in MSE
        choose_peaks = False
        if expr_peaks is not None:
            if mse_fs < mse_peaks:
                # If forward selection improves significantly (>3%), choose it; else choose peaks
                if mse_fs <= 0.97 * mse_peaks:
                    choose_peaks = False
                else:
                    choose_peaks = True
            else:
                choose_peaks = True
        else:
            choose_peaks = False

        if choose_peaks:
            expression = expr_peaks
            predictions = pred_peaks
            details = {
                "method": "peaks_triple",
                "mse": mse_peaks,
            }
        else:
            expression = expr_fs
            predictions = preds_fs
            details = {
                "method": "forward_selection",
                "selected_terms": exprs_fs,
                "coefficients": [float(c) for c in coefs_fs.tolist()],
                "mse": float(mse_fs),
            }

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details,
        }
