import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 42))
        self.k_folds = int(kwargs.get("k_folds", 5))
        self.max_total_terms = int(kwargs.get("max_total_terms", 18))
        self.radial_ws = kwargs.get("radial_ws", [0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0])
        self.linear_ws = kwargs.get("linear_ws", [0.5, 1.0, 2.0, 3.0, 4.0])
        self.cross_ws = kwargs.get("cross_ws", [0.5, 1.0, 2.0, 3.0])
        self.alphas = kwargs.get("alphas", np.logspace(-8, 2, 16))

    def _format_float(self, x, tol=1e-12):
        if abs(x) < tol:
            return "0.0"
        return f"{x:.12g}"

    def _ridge_fit(self, A, y, alpha):
        n, p = A.shape
        s = A.std(axis=0)
        s[s < 1e-12] = 1.0
        G = A / s
        ones = np.ones(n)
        B = np.column_stack([G, ones])
        K = B.T @ B
        # Penalize only feature coefficients, not intercept
        K[:p, :p] += alpha * np.eye(p)
        rhs = B.T @ y
        try:
            theta = np.linalg.solve(K, rhs)
        except np.linalg.LinAlgError:
            theta = np.linalg.lstsq(K, rhs, rcond=None)[0]
        b_scaled = theta[:p]
        c = theta[p]
        b = b_scaled / s
        return b, c

    def _ridge_cv(self, A, y, alphas, k_folds, seed):
        n = A.shape[0]
        rng = np.random.default_rng(seed)
        idx = np.arange(n)
        rng.shuffle(idx)
        folds = np.array_split(idx, k_folds)
        best_alpha = alphas[0]
        best_mse = np.inf
        for alpha in alphas:
            mse_sum = 0.0
            for k in range(k_folds):
                val_idx = folds[k]
                tr_idx = np.concatenate([folds[i] for i in range(k_folds) if i != k], axis=0)
                A_tr, y_tr = A[tr_idx], y[tr_idx]
                A_val, y_val = A[val_idx], y[val_idx]
                b, c = self._ridge_fit(A_tr, y_tr, alpha)
                y_pred = A_val @ b + c
                mse_sum += np.mean((y_val - y_pred) ** 2)
            mse = mse_sum / k_folds
            if mse < best_mse:
                best_mse = mse
                best_alpha = alpha
        return best_alpha

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0]
        x2 = X[:, 1]
        r2 = x1**2 + x2**2
        r2_expr = "(x1**2 + x2**2)"

        # Build features
        features = []
        # Helper to add features
        def add_plain(expr, values):
            features.append({
                "group": "plain",
                "expr": expr,
                "values": values,
                "is_denom": False
            })
        def add_denom(expr_num, values_num):
            # Full value used in training is values_num / (1 + r2)
            values = values_num / (1.0 + r2)
            features.append({
                "group": "denom",
                "expr_num": expr_num,
                "values": values,
                "values_num": values_num,
                "is_denom": True
            })

        # Radial sin/cos plain and r2*sin/cos
        for w in self.radial_ws:
            sw = np.sin(w * r2)
            cw = np.cos(w * r2)
            add_plain(f"sin({self._format_float(w)}*{r2_expr})", sw)
            add_plain(f"cos({self._format_float(w)}*{r2_expr})", cw)
            add_plain(f"({r2_expr})*sin({self._format_float(w)}*{r2_expr})", r2 * sw)
            add_plain(f"({r2_expr})*cos({self._format_float(w)}*{r2_expr})", r2 * cw)

        # Linear sin/cos on x1, x2
        for w in self.linear_ws:
            sw1 = np.sin(w * x1)
            cw1 = np.cos(w * x1)
            sw2 = np.sin(w * x2)
            cw2 = np.cos(w * x2)
            wf = self._format_float(w)
            add_plain(f"sin({wf}*x1)", sw1)
            add_plain(f"cos({wf}*x1)", cw1)
            add_plain(f"sin({wf}*x2)", sw2)
            add_plain(f"cos({wf}*x2)", cw2)

        # Cross sin/cos on x1+x2 and x1-x2
        s_sum = x1 + x2
        s_diff = x1 - x2
        for w in self.cross_ws:
            wf = self._format_float(w)
            add_plain(f"sin({wf}*(x1 + x2))", np.sin(w * s_sum))
            add_plain(f"cos({wf}*(x1 + x2))", np.cos(w * s_sum))
            add_plain(f"sin({wf}*(x1 - x2))", np.sin(w * s_diff))
            add_plain(f"cos({wf}*(x1 - x2))", np.cos(w * s_diff))

        # Log radial
        add_plain(f"log(1 + {r2_expr})", np.log(1.0 + r2))

        # Denominator group: 1/(1 + r2)
        add_denom("1", np.ones_like(r2))
        for w in self.radial_ws:
            wf = self._format_float(w)
            sw = np.sin(w * r2)
            cw = np.cos(w * r2)
            add_denom(f"sin({wf}*{r2_expr})", sw)
            add_denom(f"cos({wf}*{r2_expr})", cw)

        # Assemble design matrix A (without explicit intercept; we'll add it in ridge)
        A_cols = [f["values"] for f in features]
        if len(A_cols) == 0:
            # Fallback linear model
            A_lin = np.column_stack([x1, x2, np.ones_like(x1)])
            coef, _, _, _ = np.linalg.lstsq(A_lin, y, rcond=None)
            a, b, c = coef
            expr = f"{self._format_float(a)}*x1 + {self._format_float(b)}*x2 + {self._format_float(c)}"
            preds = A_lin @ coef
            return {"expression": expr, "predictions": preds.tolist(), "details": {}}

        A = np.column_stack(A_cols)

        # Cross-validated ridge to select alpha
        alpha = self._ridge_cv(A, y, np.array(self.alphas, dtype=float), self.k_folds, self.random_state)

        # Fit ridge on full data
        b_ridge, c_ridge = self._ridge_fit(A, y, alpha)

        # Feature selection by effect size
        std_cols = A.std(axis=0)
        std_cols[std_cols < 1e-12] = 1.0
        effects = np.abs(b_ridge * std_cols)
        order = np.argsort(-effects)
        k_keep = min(self.max_total_terms, A.shape[1])
        sel_idx = order[:k_keep]

        # Refit OLS on selected features
        A_sel = A[:, sel_idx]
        ones = np.ones(A_sel.shape[0])
        A_ext = np.column_stack([A_sel, ones])
        theta, _, _, _ = np.linalg.lstsq(A_ext, y, rcond=None)
        b_sel = theta[:-1]
        c_sel = theta[-1]
        y_pred = A_sel @ b_sel + c_sel

        # Build expression
        # Separate selected features into plain and denom
        plain_terms = []
        denom_terms = []
        denom_const = 0.0
        denom_const_selected = False

        for idx, coef in zip(sel_idx, b_sel):
            if abs(coef) < 1e-12:
                continue
            f = features[idx]
            if f["group"] == "plain":
                plain_terms.append((coef, f["expr"]))
            else:
                # denom group
                if f.get("expr_num") == "1":
                    denom_const += coef
                    denom_const_selected = True
                else:
                    denom_terms.append((coef, f["expr_num"]))

        # Build base expression string
        terms_str = []
        if abs(c_sel) >= 1e-12:
            terms_str.append(self._format_float(c_sel))
        for coef, expr in plain_terms:
            terms_str.append(f"({self._format_float(coef)})*({expr})")
        if len(terms_str) == 0:
            base_expr = "0.0"
        else:
            base_expr = " + ".join(terms_str)

        # Build numerator for denominator part
        num_terms = []
        if denom_const_selected and abs(denom_const) >= 1e-12:
            num_terms.append(self._format_float(denom_const))
        for coef, expr_num in denom_terms:
            num_terms.append(f"({self._format_float(coef)})*({expr_num})")

        if len(num_terms) > 0:
            num_expr = " + ".join(num_terms)
            final_expr = f"({base_expr}) + ({num_expr})/(1 + {r2_expr})"
        else:
            final_expr = f"{base_expr}"

        return {
            "expression": final_expr,
            "predictions": y_pred.tolist(),
            "details": {}
        }
