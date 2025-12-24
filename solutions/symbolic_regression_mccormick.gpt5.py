import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.use_pysr = kwargs.get("use_pysr", False)
        self.random_state = kwargs.get("random_state", 42)
        self.pysr_params = kwargs.get("pysr_params", {})
        self._tiny = 1e-12

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        x1, x2 = X[:, 0], X[:, 1]

        best = {
            "expression": None,
            "predictions": None,
            "mse": np.inf,
            "method": None
        }

        # Candidate 1: Canonical McCormick expression
        canonical_expr = "sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1"
        preds = self._eval_expr(canonical_expr, x1, x2)
        if preds is not None:
            mse = self._mse(y, preds)
            if mse < best["mse"]:
                best.update(expression=canonical_expr, predictions=preds, mse=mse, method="canonical")

        # If canonical is already very good, return early
        y_var = np.var(y) + self._tiny
        if best["mse"] / y_var < 1e-6:
            return {
                "expression": best["expression"],
                "predictions": best["predictions"].tolist(),
                "details": {"method": best["method"], "mse": float(best["mse"])}
            }

        # Candidate 2: Fit McCormick-basis linear regression
        expr_mc, preds_mc, mse_mc = self._fit_mccormick_basis(x1, x2, y)
        if mse_mc < best["mse"]:
            best.update(expression=expr_mc, predictions=preds_mc, mse=mse_mc, method="mccormick_basis")

        # Optional PySR if requested or if fit is poor
        if self.use_pysr or (best["mse"] / y_var > 1e-3):
            expr_sr, preds_sr, mse_sr = self._try_pysr(X, y)
            if expr_sr is not None and mse_sr < best["mse"]:
                best.update(expression=expr_sr, predictions=preds_sr, mse=mse_sr, method="pysr")

        return {
            "expression": best["expression"],
            "predictions": best["predictions"].tolist(),
            "details": {"method": best["method"], "mse": float(best["mse"])}
        }

    def _fit_mccormick_basis(self, x1, x2, y):
        # Features tailored to McCormick form
        f1 = np.sin(x1 + x2)
        f2 = (x1 - x2) ** 2
        f3 = x1
        f4 = x2
        f5 = np.ones_like(x1)
        A = np.column_stack([f1, f2, f3, f4, f5])

        coefs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        # Drop near-zero coefficients to simplify expression
        mask = np.abs(coefs) > 1e-10
        terms = ["sin(x1 + x2)", "(x1 - x2)**2", "x1", "x2", "1"]
        expr = self._build_linear_expression(coefs, terms, mask)

        preds = self._eval_expr(expr, x1, x2)
        mse = self._mse(y, preds)
        return expr, preds, mse

    def _build_linear_expression(self, coefs, term_strs, mask=None):
        def fmt_num(v):
            # Prefer clean numbers
            if np.isfinite(v):
                # Snap to integers or halves if close
                rounded_int = np.round(v)
                if np.isclose(v, rounded_int, atol=1e-9, rtol=0):
                    return str(int(rounded_int))
                half = np.round(v * 2) / 2.0
                if np.isclose(v, half, atol=1e-9, rtol=0):
                    return f"{half:.12g}"
                return f"{v:.12g}"
            return "0"

        pieces = []
        for c, t in zip(coefs, term_strs):
            if mask is not None and not mask[list(term_strs).index(t)]:
                continue
            if abs(c) < 1e-12:
                continue
            if t == "1":
                pieces.append(c)
            else:
                if np.isclose(abs(c), 1.0, atol=1e-10, rtol=0):
                    pieces.append(np.sign(c) * 1.0 * (0 if t == "1" else 1))
                    # Append with sign handled later; store marker as tuple
                    pieces[-1] = ("term", np.sign(c), t, None)
                else:
                    pieces.append(("term", np.sign(c), t, abs(c)))

        # Convert to string with correct signs
        expr = ""
        first = True
        for p in pieces:
            if isinstance(p, tuple) and p[0] == "term":
                sign = p[1]
                term = p[2]
                mag = p[3]
                if mag is None:
                    term_str = term
                else:
                    term_str = f"{fmt_num(mag)}*{term}"
                if first:
                    expr = f"-{term_str}" if sign < 0 else term_str
                    first = False
                else:
                    expr += f" - {term_str}" if sign < 0 else f" + {term_str}"
            else:
                # Constant
                c = float(p)
                if first:
                    expr = fmt_num(c)
                    first = False
                else:
                    expr += f" - {fmt_num(-c)}" if c < 0 else f" + {fmt_num(c)}"

        if expr == "":
            expr = "0"
        return expr

    def _eval_expr(self, expr, x1, x2):
        local_dict = {
            "x1": x1,
            "x2": x2,
            "sin": np.sin,
            "cos": np.cos,
            "exp": np.exp,
            "log": np.log,
        }
        try:
            return eval(expr, {"__builtins__": {}}, local_dict)
        except Exception:
            return None

    def _mse(self, y_true, y_pred):
        if y_pred is None:
            return np.inf
        diff = y_true - y_pred
        return float(np.mean(diff * diff))

    def _try_pysr(self, X, y):
        try:
            from pysr import PySRRegressor
        except Exception:
            return None, None, np.inf

        params = dict(
            niterations=40,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=33,
            maxsize=25,
            verbosity=0,
            progress=False,
            random_state=self.random_state,
            warm_start=False,
        )
        params.update(self.pysr_params)

        try:
            model = PySRRegressor(**params)
            model.fit(X, y, variable_names=["x1", "x2"])
            expr_sympy = model.sympy()
            expression = str(expr_sympy)
            preds = model.predict(X)
            mse = self._mse(y, preds)
            return expression, preds, mse
        except Exception:
            return None, None, np.inf
