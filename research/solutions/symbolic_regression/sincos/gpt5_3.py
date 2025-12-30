import numpy as np
import math
import ast

class Solution:
    def __init__(self, **kwargs):
        self.max_terms = kwargs.get("max_terms", 6)
        self.random_state = kwargs.get("random_state", 42)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).ravel()
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Build candidate feature dictionary
        features = {
            "1": np.ones(n),
            "x1": x1,
            "x2": x2,
            "sin(x1)": np.sin(x1),
            "cos(x1)": np.cos(x1),
            "sin(x2)": np.sin(x2),
            "cos(x2)": np.cos(x2),
            "sin(x1 + x2)": np.sin(x1 + x2),
            "cos(x1 + x2)": np.cos(x1 + x2),
            "sin(x1 - x2)": np.sin(x1 - x2),
            "cos(x1 - x2)": np.cos(x1 - x2),
            "sin(2*x1)": np.sin(2.0 * x1),
            "cos(2*x1)": np.cos(2.0 * x1),
            "sin(2*x2)": np.sin(2.0 * x2),
            "cos(2*x2)": np.cos(2.0 * x2),
        }

        # Orthogonal Matching Pursuit for sparse selection
        coef_map = self._omp(features, y, max_terms=self.max_terms)

        # Build expression from selected coefficients with simplifications
        expr = self._build_expression_from_coefs(coef_map)

        # Fallbacks if expression empty or invalid
        if not expr or not isinstance(expr, str) or expr.strip() == "":
            expr = str(float(np.mean(y)))

        # Compute predictions from expression
        predictions = self._eval_expression(expr, X)
        if predictions is None:
            # Safe fallback to a constant model
            mean_y = float(np.mean(y))
            expr = self._format_number(mean_y)
            predictions = np.full_like(y, mean_y, dtype=float)

        # Compute complexity
        complexity = self._compute_complexity(expr)

        return {
            "expression": expr,
            "predictions": predictions.tolist(),
            "details": {"complexity": int(complexity)}
        }

    def _omp(self, features_dict, y, max_terms=6, tol=1e-12):
        # Prepare feature names and vectors
        names = list(features_dict.keys())
        # Ensure deterministic order: constants, basics, sums/diffs, doubles
        order = ["1", "x1", "x2",
                 "sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)",
                 "sin(x1 + x2)", "cos(x1 + x2)", "sin(x1 - x2)", "cos(x1 - x2)",
                 "sin(2*x1)", "cos(2*x1)", "sin(2*x2)", "cos(2*x2)"]
        names = [n for n in order if n in features_dict]

        cols = [np.asarray(features_dict[n], dtype=float).ravel() for n in names]
        norms = [np.linalg.norm(c) + 1e-18 for c in cols]
        y = np.asarray(y, dtype=float).ravel()
        var_y = np.var(y) + 1e-18

        active_idx = []
        # Start with intercept if available
        if "1" in names:
            active_idx.append(names.index("1"))

        coef = None
        A_active = None

        for _ in range(max_terms):
            # Compute residual
            if active_idx:
                A_active = np.column_stack([cols[i] for i in active_idx])
                coef, _, _, _ = np.linalg.lstsq(A_active, y, rcond=None)
                residual = y - A_active.dot(coef)
            else:
                residual = y.copy()

            mse = float(np.mean(residual**2))
            if mse <= tol * max(1.0, var_y):
                break

            # Select next feature by maximum absolute normalized correlation
            best_score = -1.0
            best_j = None
            for j, v in enumerate(cols):
                if j in active_idx:
                    continue
                score = abs(float(np.dot(v, residual))) / norms[j]
                if score > best_score:
                    best_score = score
                    best_j = j

            if best_j is None:
                break

            # Check if addition of best feature significantly improves fit
            prev_mse = mse
            candidate_active = active_idx + [best_j]
            A_cand = np.column_stack([cols[i] for i in candidate_active])
            coef_cand, _, _, _ = np.linalg.lstsq(A_cand, y, rcond=None)
            residual_cand = y - A_cand.dot(coef_cand)
            mse_cand = float(np.mean(residual_cand**2))

            # If not improved, stop
            if prev_mse - mse_cand <= 1e-14:
                break

            active_idx.append(best_j)

        # Final coefficients
        if active_idx:
            A_active = np.column_stack([cols[i] for i in active_idx])
            coef, _, _, _ = np.linalg.lstsq(A_active, y, rcond=None)
        else:
            coef = np.array([])

        coef_map = {}
        for idx, c in zip(active_idx, coef):
            # Threshold tiny coefficients
            if abs(c) > 1e-12:
                coef_map[names[idx]] = float(c)
        return coef_map

    def _build_expression_from_coefs(self, coef_map):
        if not coef_map:
            return ""

        # Prepare grouping sin/cos by angle
        groups = {}
        others = {}
        const_val = coef_map.get("1", 0.0)

        def is_trig(name):
            return name.startswith("sin(") or name.startswith("cos(")

        for name, c in coef_map.items():
            if name == "1":
                continue
            if is_trig(name):
                if name.startswith("sin("):
                    arg = name[4:-1]
                    g = groups.setdefault(arg, {"sin": 0.0, "cos": 0.0})
                    g["sin"] += c
                else:
                    arg = name[4:-1]
                    g = groups.setdefault(arg, {"sin": 0.0, "cos": 0.0})
                    g["cos"] += c
            else:
                # variables x1 or x2
                others[name] = c

        # Create terms
        terms = []

        # Process groups: combine sin and cos of same argument into amplitude-phase when both present
        for arg, sc in groups.items():
            s = sc.get("sin", 0.0)
            c = sc.get("cos", 0.0)
            if abs(s) < 1e-12 and abs(c) < 1e-12:
                continue
            if abs(s) > 1e-12 and abs(c) > 1e-12:
                R = math.hypot(s, c)
                phi = math.atan2(c, s)
                phi = self._wrap_angle(phi)
                arg_with_phi = self._arg_with_phase(arg, phi)
                base_expr = f"sin({arg_with_phi})"
                terms.append((R, base_expr))
            else:
                # Keep as-is for single sin or cos
                if abs(s) > 1e-12:
                    base_expr = f"sin({arg})"
                    terms.append((s, base_expr))
                if abs(c) > 1e-12:
                    base_expr = f"cos({arg})"
                    terms.append((c, base_expr))

        # Add variable terms
        for var in ["x1", "x2"]:
            if var in others and abs(others[var]) > 1e-12:
                terms.append((others[var], var))

        # Add constant last
        const_term = None
        if abs(const_val) > 1e-12:
            const_term = const_val

        # Build final expression string
        expr = self._join_terms(terms, const_term)

        # As a sanity: if empty, fallback to constant zero
        if not expr or expr.strip() == "":
            expr = "0"
        return expr

    def _join_terms(self, terms, const_val):
        # terms: list of (coef, base_expr) where base_expr like 'sin(...)' or 'x1' or 'x2'
        # Filter zero coefficients
        filtered = [(c, b) for (c, b) in terms if abs(c) > 1e-12]

        parts = []

        # Helper to format coefficient and term
        def term_to_str(coef, base):
            mag = abs(coef)
            # If base is a pure numeric (shouldn't be here), return it; otherwise multiply if needed
            if base in ("x1", "x2") or base.startswith("sin(") or base.startswith("cos("):
                if self._is_close(mag, 1.0):
                    t = base
                else:
                    t = f"{self._format_number(mag)}*{base}"
            else:
                # fallback
                t = f"{self._format_number(mag)}*{base}"
            return t

        # Sort for consistency: by complexity of base, then name
        def base_key(b):
            # prioritize simpler bases
            if b in ("x1", "x2"):
                return (0, b)
            if b.startswith("sin(") or b.startswith("cos("):
                # shorter argument considered simpler
                return (1, len(b), b)
            return (2, b)

        filtered.sort(key=lambda t: base_key(t[1]))

        # Build string with proper signs
        for i, (coef, base) in enumerate(filtered):
            part_str = term_to_str(coef, base)
            if i == 0:
                if coef < 0:
                    parts.append("-" + part_str)
                else:
                    parts.append(part_str)
            else:
                if coef < 0:
                    parts.append(" - " + part_str)
                else:
                    parts.append(" + " + part_str)

        # Constant term
        if const_val is not None and abs(const_val) > 1e-12:
            const_str = self._format_number(abs(const_val))
            if not parts:
                parts.append(const_str if const_val >= 0 else "-" + const_str)
            else:
                if const_val >= 0:
                    parts.append(" + " + const_str)
                else:
                    parts.append(" - " + const_str)

        if not parts:
            return "0"
        return "".join(parts)

    def _wrap_angle(self, phi):
        # wrap to [-pi, pi]
        two_pi = 2.0 * math.pi
        phi = ((phi + math.pi) % two_pi) - math.pi
        # Snap very small to zero
        if abs(phi) < 1e-14:
            phi = 0.0
        return phi

    def _arg_with_phase(self, arg, phi):
        if abs(phi) < 1e-14:
            return arg
        phi_str = self._format_number(abs(phi))
        if phi >= 0:
            return f"{arg} + {phi_str}"
        else:
            return f"{arg} - {phi_str}"

    def _format_number(self, val):
        if not np.isfinite(val):
            return "0"
        if abs(val) < 1e-14:
            return "0"
        # Try integer
        r = round(val)
        if abs(val - r) < 1e-12:
            return str(int(r))
        # General float with up to 12 significant digits
        s = np.format_float_positional(val, precision=12, trim='-')
        # Remove redundant leading zeros in -0.x
        if s.startswith("-0.") and len(s) > 3:
            s = "-" + s[1:]
        elif s.startswith("0.") and len(s) > 2:
            s = s[1:]
        return s

    def _is_close(self, a, b, tol=1e-12):
        return abs(a - b) <= tol

    def _eval_expression(self, expr, X):
        try:
            env = {
                "x1": X[:, 0],
                "x2": X[:, 1],
                "sin": np.sin,
                "cos": np.cos,
                "exp": np.exp,
                "log": np.log,
            }
            y_pred = eval(expr, {"__builtins__": None}, env)
            y_pred = np.asarray(y_pred, dtype=float).ravel()
            if y_pred.shape[0] != X.shape[0] or not np.all(np.isfinite(y_pred)):
                return None
            return y_pred
        except Exception:
            return None

    def _compute_complexity(self, expr):
        try:
            node = ast.parse(expr, mode='eval')
        except Exception:
            return 0

        class Counter(ast.NodeVisitor):
            def __init__(self):
                self.bin_ops = 0
                self.unary_funcs = 0

            def visit_BinOp(self, node):
                self.bin_ops += 1
                self.generic_visit(node)

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name) and node.func.id in {"sin", "cos", "exp", "log"}:
                    self.unary_funcs += 1
                self.generic_visit(node)

            def visit_UnaryOp(self, node):
                # Do not count unary +/- as per problem statement
                self.generic_visit(node)

        c = Counter()
        c.visit(node)
        return 2 * c.bin_ops + c.unary_funcs