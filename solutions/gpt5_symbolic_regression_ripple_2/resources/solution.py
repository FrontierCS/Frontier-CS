import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = kwargs.get("random_state", 42)
        self.alpha = kwargs.get("alpha", 1e-8)
        self.max_k = kwargs.get("max_k", 20.0)
        self.k_step = kwargs.get("k_step", 0.5)
        self.try_second_frequency = kwargs.get("try_second_frequency", True)
        self.second_freq_improvement = kwargs.get("second_freq_improvement", 0.97)  # 3% improvement required

    def _ridge(self, A, y, alpha=1e-8, penalize_intercept=True):
        n_features = A.shape[1]
        AtA = A.T @ A
        Aty = A.T @ y
        pen = np.ones(n_features)
        if penalize_intercept and n_features > 0:
            pen[-1] = 0.0  # do not penalize intercept
        else:
            pen[:] = 1.0
        AtA[np.diag_indices(n_features)] += alpha * pen
        try:
            w = np.linalg.solve(AtA, Aty)
        except np.linalg.LinAlgError:
            w = np.linalg.lstsq(AtA + 1e-12 * np.eye(n_features), Aty, rcond=None)[0]
        return w

    def _build_features_single(self, r, k, denom_vec, include_r_terms=True):
        s = np.sin(k * r) / denom_vec
        c = np.cos(k * r) / denom_vec
        if include_r_terms:
            A = np.column_stack([s, r * s, c, r * c, np.ones_like(r)])
        else:
            A = np.column_stack([s, c, np.ones_like(r)])
        return A

    def _build_features_two(self, r, k1, k2, denom_vec, include_r_terms=True):
        s1 = np.sin(k1 * r) / denom_vec
        c1 = np.cos(k1 * r) / denom_vec
        s2 = np.sin(k2 * r) / denom_vec
        c2 = np.cos(k2 * r) / denom_vec
        if include_r_terms:
            A = np.column_stack([
                s1, r * s1, c1, r * c1,
                s2, r * s2, c2, r * c2,
                np.ones_like(r)
            ])
        else:
            A = np.column_stack([s1, c1, s2, c2, np.ones_like(r)])
        return A

    def _denominators(self, r):
        # Returns list of tuples: (name, denom_vector, denom_expr_str)
        r_expr = "(x1**2 + x2**2)**0.5"
        denoms = []
        denoms.append(("none", np.ones_like(r), "1"))
        denoms.append(("r1", 1.0 + r, f"1 + {r_expr}"))
        denoms.append(("rsq", np.sqrt(1.0 + r * r), f"(1 + x1**2 + x2**2)**0.5"))
        denoms.append(("r01", 0.1 + r, f"0.1 + {r_expr}"))
        return denoms

    def _format_const(self, v):
        if not np.isfinite(v):
            v = 0.0
        # Use 12 significant digits to balance precision and brevity
        return f"{float(v):.12g}"

    def _build_expression_single(self, coef, k, denom_str, include_r_terms=True):
        r_expr = "(x1**2 + x2**2)**0.5"
        terms = []
        idx = 0
        if include_r_terms:
            c_s = self._format_const(coef[idx]); idx += 1
            c_rs = self._format_const(coef[idx]); idx += 1
            c_c = self._format_const(coef[idx]); idx += 1
            c_rc = self._format_const(coef[idx]); idx += 1
            bias = self._format_const(coef[idx]); idx += 1

            # s/d
            if abs(float(c_s)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_s})*sin({self._format_const(k)}*{r_expr})")
                else:
                    terms.append(f"({c_s})*sin({self._format_const(k)}*{r_expr})/({denom_str})")
            # r*s/d
            if abs(float(c_rs)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_rs})*{r_expr}*sin({self._format_const(k)}*{r_expr})")
                else:
                    terms.append(f"({c_rs})*{r_expr}*sin({self._format_const(k)}*{r_expr})/({denom_str})")
            # c/d
            if abs(float(c_c)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_c})*cos({self._format_const(k)}*{r_expr})")
                else:
                    terms.append(f"({c_c})*cos({self._format_const(k)}*{r_expr})/({denom_str})")
            # r*c/d
            if abs(float(c_rc)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_rc})*{r_expr}*cos({self._format_const(k)}*{r_expr})")
                else:
                    terms.append(f"({c_rc})*{r_expr}*cos({self._format_const(k)}*{r_expr})/({denom_str})")
            if abs(float(bias)) > 1e-12 or not terms:
                terms.append(f"({bias})")
        else:
            c_s = self._format_const(coef[idx]); idx += 1
            c_c = self._format_const(coef[idx]); idx += 1
            bias = self._format_const(coef[idx]); idx += 1

            if abs(float(c_s)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_s})*sin({self._format_const(k)}*{r_expr})")
                else:
                    terms.append(f"({c_s})*sin({self._format_const(k)}*{r_expr})/({denom_str})")
            if abs(float(c_c)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_c})*cos({self._format_const(k)}*{r_expr})")
                else:
                    terms.append(f"({c_c})*cos({self._format_const(k)}*{r_expr})/({denom_str})")
            if abs(float(bias)) > 1e-12 or not terms:
                terms.append(f"({bias})")

        expression = " + ".join(terms) if terms else "0"
        return expression

    def _build_expression_two(self, coef, k1, k2, denom_str, include_r_terms=True):
        r_expr = "(x1**2 + x2**2)**0.5"
        terms = []
        idx = 0
        if include_r_terms:
            # k1
            c_s1 = self._format_const(coef[idx]); idx += 1
            c_rs1 = self._format_const(coef[idx]); idx += 1
            c_c1 = self._format_const(coef[idx]); idx += 1
            c_rc1 = self._format_const(coef[idx]); idx += 1
            # k2
            c_s2 = self._format_const(coef[idx]); idx += 1
            c_rs2 = self._format_const(coef[idx]); idx += 1
            c_c2 = self._format_const(coef[idx]); idx += 1
            c_rc2 = self._format_const(coef[idx]); idx += 1

            bias = self._format_const(coef[idx]); idx += 1

            if abs(float(c_s1)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_s1})*sin({self._format_const(k1)}*{r_expr})")
                else:
                    terms.append(f"({c_s1})*sin({self._format_const(k1)}*{r_expr})/({denom_str})")
            if abs(float(c_rs1)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_rs1})*{r_expr}*sin({self._format_const(k1)}*{r_expr})")
                else:
                    terms.append(f"({c_rs1})*{r_expr}*sin({self._format_const(k1)}*{r_expr})/({denom_str})")
            if abs(float(c_c1)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_c1})*cos({self._format_const(k1)}*{r_expr})")
                else:
                    terms.append(f"({c_c1})*cos({self._format_const(k1)}*{r_expr})/({denom_str})")
            if abs(float(c_rc1)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_rc1})*{r_expr}*cos({self._format_const(k1)}*{r_expr})")
                else:
                    terms.append(f"({c_rc1})*{r_expr}*cos({self._format_const(k1)}*{r_expr})/({denom_str})")

            if abs(float(c_s2)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_s2})*sin({self._format_const(k2)}*{r_expr})")
                else:
                    terms.append(f"({c_s2})*sin({self._format_const(k2)}*{r_expr})/({denom_str})")
            if abs(float(c_rs2)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_rs2})*{r_expr}*sin({self._format_const(k2)}*{r_expr})")
                else:
                    terms.append(f"({c_rs2})*{r_expr}*sin({self._format_const(k2)}*{r_expr})/({denom_str})")
            if abs(float(c_c2)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_c2})*cos({self._format_const(k2)}*{r_expr})")
                else:
                    terms.append(f"({c_c2})*cos({self._format_const(k2)}*{r_expr})/({denom_str})")
            if abs(float(c_rc2)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_rc2})*{r_expr}*cos({self._format_const(k2)}*{r_expr})")
                else:
                    terms.append(f"({c_rc2})*{r_expr}*cos({self._format_const(k2)}*{r_expr})/({denom_str})")

            if abs(float(bias)) > 1e-12 or not terms:
                terms.append(f"({bias})")
        else:
            c_s1 = self._format_const(coef[idx]); idx += 1
            c_c1 = self._format_const(coef[idx]); idx += 1
            c_s2 = self._format_const(coef[idx]); idx += 1
            c_c2 = self._format_const(coef[idx]); idx += 1
            bias = self._format_const(coef[idx]); idx += 1

            if abs(float(c_s1)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_s1})*sin({self._format_const(k1)}*{r_expr})")
                else:
                    terms.append(f"({c_s1})*sin({self._format_const(k1)}*{r_expr})/({denom_str})")
            if abs(float(c_c1)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_c1})*cos({self._format_const(k1)}*{r_expr})")
                else:
                    terms.append(f"({c_c1})*cos({self._format_const(k1)}*{r_expr})/({denom_str})")

            if abs(float(c_s2)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_s2})*sin({self._format_const(k2)}*{r_expr})")
                else:
                    terms.append(f"({c_s2})*sin({self._format_const(k2)}*{r_expr})/({denom_str})")
            if abs(float(c_c2)) > 1e-12:
                if denom_str == "1":
                    terms.append(f"({c_c2})*cos({self._format_const(k2)}*{r_expr})")
                else:
                    terms.append(f"({c_c2})*cos({self._format_const(k2)}*{r_expr})/({denom_str})")

            if abs(float(bias)) > 1e-12 or not terms:
                terms.append(f"({bias})")

        expression = " + ".join(terms) if terms else "0"
        return expression

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]
        r = np.sqrt(x1 * x1 + x2 * x2)

        # Baseline linear model for fallback
        A_lin = np.column_stack([x1, x2, np.ones_like(x1)])
        try:
            coeffs_lin, _, _, _ = np.linalg.lstsq(A_lin, y, rcond=None)
            yhat_lin = A_lin @ coeffs_lin
            mse_lin = float(np.mean((y - yhat_lin) ** 2))
        except np.linalg.LinAlgError:
            coeffs_lin = np.array([0.0, 0.0, float(np.mean(y))])
            yhat_lin = coeffs_lin[2] * np.ones_like(y)
            mse_lin = float(np.mean((y - yhat_lin) ** 2))

        # Search over single-frequency models
        k_values = np.arange(1.0, self.max_k + 1e-9, self.k_step)
        denominators = self._denominators(r)
        best_single = {
            "mse": np.inf,
            "coef": None,
            "k": None,
            "denom_name": None,
            "denom_str": None,
            "include_r_terms": True,
            "pred": None
        }

        include_r_terms = True  # allow r*trig terms for amplitude modulation

        for denom_name, denom_vec, denom_str in denominators:
            for k in k_values:
                A = self._build_features_single(r, k, denom_vec, include_r_terms=include_r_terms)
                coef = self._ridge(A, y, alpha=self.alpha, penalize_intercept=True)
                pred = A @ coef
                mse = float(np.mean((y - pred) ** 2))
                if mse < best_single["mse"]:
                    best_single.update({
                        "mse": mse,
                        "coef": coef,
                        "k": k,
                        "denom_name": denom_name,
                        "denom_str": denom_str,
                        "include_r_terms": include_r_terms,
                        "pred": pred
                    })

        # Optionally search for two-frequency model using the best single's denominator
        best_two = None
        if self.try_second_frequency and best_single["coef"] is not None:
            denom = [d for d in denominators if d[0] == best_single["denom_name"]][0]
            denom_vec = denom[1]
            denom_str = denom[2]
            k1 = best_single["k"]
            best_two = {
                "mse": best_single["mse"],
                "coef": None,
                "k1": None,
                "k2": None,
                "denom_str": denom_str,
                "include_r_terms": include_r_terms,
                "pred": None
            }
            for k2 in k_values:
                if abs(k2 - k1) < 1e-12:
                    continue
                A2 = self._build_features_two(r, k1, k2, denom_vec, include_r_terms=include_r_terms)
                coef2 = self._ridge(A2, y, alpha=self.alpha, penalize_intercept=True)
                pred2 = A2 @ coef2
                mse2 = float(np.mean((y - pred2) ** 2))
                if mse2 < best_two["mse"]:
                    best_two.update({
                        "mse": mse2,
                        "coef": coef2,
                        "k1": k1,
                        "k2": k2,
                        "pred": pred2
                    })

            # Only use the two-frequency model if it meaningfully improves MSE
            if best_two["coef"] is not None and best_two["mse"] <= self.second_freq_improvement * best_single["mse"]:
                chosen_model = ("two", best_two)
            else:
                chosen_model = ("single", best_single)
        else:
            chosen_model = ("single", best_single)

        # Compare with linear baseline; pick the better
        chosen_type, chosen_info = chosen_model
        chosen_mse = chosen_info["mse"] if chosen_info["mse"] is not None else np.inf

        if mse_lin < chosen_mse:
            # Baseline linear model wins
            a, b, c = coeffs_lin
            expr = f"{self._format_const(a)}*x1 + {self._format_const(b)}*x2 + {self._format_const(c)}"
            predictions = yhat_lin
            details = {"model": "linear_baseline", "mse": mse_lin}
        else:
            # Build symbolic expression from chosen radial harmonic model
            if chosen_type == "single":
                expr = self._build_expression_single(
                    chosen_info["coef"],
                    chosen_info["k"],
                    chosen_info["denom_str"],
                    include_r_terms=chosen_info["include_r_terms"]
                )
                predictions = chosen_info["pred"]
                details = {
                    "model": "single_frequency",
                    "k": chosen_info["k"],
                    "denominator": chosen_info["denom_name"],
                    "mse": chosen_info["mse"]
                }
            else:
                expr = self._build_expression_two(
                    chosen_info["coef"],
                    chosen_info["k1"],
                    chosen_info["k2"],
                    chosen_info["denom_str"],
                    include_r_terms=chosen_info["include_r_terms"]
                )
                predictions = chosen_info["pred"]
                details = {
                    "model": "two_frequency",
                    "k1": chosen_info["k1"],
                    "k2": chosen_info["k2"],
                    "denominator": best_single["denom_name"],
                    "mse": chosen_info["mse"]
                }

        return {
            "expression": expr,
            "predictions": predictions.tolist(),
            "details": details
        }
