import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.tol_coef = kwargs.get("tol_coef", 1e-10)
        self.grid_c1 = kwargs.get("grid_c1", [0.9, 1.0, 1.1])
        self.grid_a3 = kwargs.get("grid_a3", [0.9, 1.0, 1.1])
        self.grid_b3 = kwargs.get("grid_b3", [-0.1, 0.0, 0.1])
        self.rbf_centers = kwargs.get("rbf_centers", [-1.0, 0.0, 1.0])
        self.rbf_k_values = kwargs.get("rbf_k_values", [0.5, 1.0])
        self.use_rbf_threshold_ratio = kwargs.get("use_rbf_threshold_ratio", 0.9)
        self.pick_rbf_improve_ratio = kwargs.get("pick_rbf_improve_ratio", 0.75)

    @staticmethod
    def _safe_lstsq(A, y):
        return np.linalg.lstsq(A, y, rcond=None)[0]

    @staticmethod
    def _compute_mse(y_true, y_pred):
        diff = y_true - y_pred
        return float(np.mean(diff * diff))

    def _build_peaks_features(self, x1, x2, c1, a3, b3):
        t1 = (1.0 - x1) ** 2
        e1 = np.exp(-((x1 ** 2) + (x2 + c1) ** 2))
        phi1 = t1 * e1

        poly2 = (0.2 * x1 - x1 ** 3 - x2 ** 5)
        e2 = np.exp(-((x1 ** 2) + (x2 ** 2)))
        phi2 = poly2 * e2

        e3 = np.exp(-((x1 + a3) ** 2 + (x2 + b3) ** 2))
        phi3 = e3

        return phi1, phi2, phi3

    def _fit_peaks_grid(self, x1, x2, y):
        ones = np.ones_like(y)
        best = None
        for c1 in self.grid_c1:
            for a3 in self.grid_a3:
                for b3 in self.grid_b3:
                    phi1, phi2, phi3 = self._build_peaks_features(x1, x2, c1, a3, b3)
                    A = np.column_stack([phi1, phi2, phi3, ones])
                    coeffs = self._safe_lstsq(A, y)
                    yhat = A @ coeffs
                    mse = self._compute_mse(y, yhat)
                    if (best is None) or (mse < best["mse"]):
                        best = {
                            "mse": mse,
                            "coeffs": coeffs,
                            "params": (c1, a3, b3),
                            "pred": yhat,
                        }
        return best

    def _evaluate_peaks_exact(self, x1, x2, y):
        # Classic MATLAB "peaks" function coefficients
        c1, a3, b3 = 1.0, 1.0, 0.0
        phi1, phi2, phi3 = self._build_peaks_features(x1, x2, c1, a3, b3)
        yhat = 3.0 * phi1 - 10.0 * phi2 - (1.0 / 3.0) * phi3
        mse = self._compute_mse(y, yhat)
        return {
            "mse": mse,
            "coeffs": np.array([3.0, -10.0, -(1.0 / 3.0), 0.0], dtype=float),
            "params": (c1, a3, b3),
            "pred": yhat,
        }

    def _fit_linear_baseline(self, x1, x2, y):
        A = np.column_stack([x1, x2, np.ones_like(y)])
        coeffs = self._safe_lstsq(A, y)
        yhat = A @ coeffs
        mse = self._compute_mse(y, yhat)
        return mse, coeffs, yhat

    def _fit_rbf(self, x1, x2, y):
        ones = np.ones_like(y)
        best = None
        grid = self.rbf_centers
        for k in self.rbf_k_values:
            features = []
            centers = []
            for cx in grid:
                for cy in grid:
                    phi = np.exp(-k * ((x1 - cx) ** 2 + (x2 - cy) ** 2))
                    features.append(phi)
                    centers.append((cx, cy))
            if len(features) == 0:
                continue
            A = np.column_stack(features + [ones])
            coeffs = self._safe_lstsq(A, y)
            yhat = A @ coeffs
            mse = self._compute_mse(y, yhat)
            if (best is None) or (mse < best["mse"]):
                best = {
                    "mse": mse,
                    "coeffs": coeffs,
                    "k": k,
                    "centers": centers,
                    "pred": yhat,
                }
        return best

    @staticmethod
    def _float_to_str(val):
        if not np.isfinite(val):
            return "0"
        if abs(val) < 1e-14:
            return "0"
        # Prefer concise representation
        s = np.format_float_positional(val, precision=12, trim='-')
        # Ensure there's a decimal or exponent to distinguish from ints
        if ('e' not in s) and ('.' not in s):
            s = s + ".0"
        return s

    def _build_expression_peaks(self, coeffs, params):
        a, b, c, d = [float(x) for x in coeffs]
        c1, a3, b3 = params

        terms = []

        if abs(a) > self.tol_coef:
            a_str = self._float_to_str(a)
            c1_str = self._float_to_str(c1)
            term = f"{a_str}*((1 - x1)**2)*exp(-((x1**2) + (x2 + {c1_str})**2))"
            terms.append(term)

        if abs(b) > self.tol_coef:
            b_str = self._float_to_str(b)
            term = f"{b_str}*((0.2*x1 - x1**3 - x2**5)*exp(-((x1**2) + (x2**2))))"
            terms.append(term)

        if abs(c) > self.tol_coef:
            c_str = self._float_to_str(c)
            a3_str = self._float_to_str(a3)
            b3_str = self._float_to_str(b3)
            term = f"{c_str}*exp(-(((x1 + {a3_str})**2) + ((x2 + {b3_str})**2)))"
            terms.append(term)

        if abs(d) > self.tol_coef:
            d_str = self._float_to_str(d)
            terms.append(d_str)

        if not terms:
            return "0"
        return " + ".join(terms)

    def _build_expression_rbf(self, coeffs, k, centers):
        terms = []
        k_str = self._float_to_str(k)
        # Last coefficient is intercept
        for coef, (cx, cy) in zip(coeffs[:-1], centers):
            if abs(coef) <= self.tol_coef:
                continue
            c_str = self._float_to_str(float(coef))
            cx_str = self._float_to_str(cx)
            cy_str = self._float_to_str(cy)
            term = f"{c_str}*exp(-({k_str})*(((x1 - {cx_str})**2) + ((x2 - {cy_str})**2)))"
            terms.append(term)
        intercept = float(coeffs[-1])
        if abs(intercept) > self.tol_coef:
            terms.append(self._float_to_str(intercept))
        if not terms:
            return "0"
        return " + ".join(terms)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Baseline linear model
        baseline_mse, _, _ = self._fit_linear_baseline(x1, x2, y)

        # Peaks exact (fixed coefficients)
        exact_result = self._evaluate_peaks_exact(x1, x2, y)

        # Peaks with fitted amplitudes and slight center tweaks
        peaks_fit = self._fit_peaks_grid(x1, x2, y)

        # Choose between exact and fitted peaks
        if peaks_fit["mse"] <= exact_result["mse"]:
            best_expr = self._build_expression_peaks(peaks_fit["coeffs"], peaks_fit["params"])
            best_pred = peaks_fit["pred"]
            best_mse = peaks_fit["mse"]
        else:
            best_expr = self._build_expression_peaks(exact_result["coeffs"], exact_result["params"])
            best_pred = exact_result["pred"]
            best_mse = exact_result["mse"]

        # Consider RBF fallback if peaks not clearly better than linear baseline
        rbf_chosen = False
        if best_mse > self.use_rbf_threshold_ratio * baseline_mse:
            rbf_fit = self._fit_rbf(x1, x2, y)
            if rbf_fit is not None and rbf_fit["mse"] < self.pick_rbf_improve_ratio * best_mse:
                rbf_expr = self._build_expression_rbf(rbf_fit["coeffs"], rbf_fit["k"], rbf_fit["centers"])
                rbf_pred = rbf_fit["pred"]
                # Choose RBF if substantially better in MSE
                best_expr = rbf_expr
                best_pred = rbf_pred
                best_mse = rbf_fit["mse"]
                rbf_chosen = True

        result = {
            "expression": best_expr,
            "predictions": best_pred.tolist(),
            "details": {
                "mse": best_mse,
                "baseline_mse": baseline_mse,
                "used_rbf": rbf_chosen,
            },
        }
        return result