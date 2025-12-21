import numpy as np


class Solution:
    def __init__(self, **kwargs):
        pass

    def _fit_with_pysr(self, X: np.ndarray, y: np.ndarray):
        try:
            from pysr import PySRRegressor
        except Exception:
            return None, None

        try:
            n_samples = X.shape[0]
            if n_samples < 1000:
                niterations = 70
            elif n_samples < 5000:
                niterations = 50
            else:
                niterations = 35

            model = PySRRegressor(
                niterations=niterations,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=15,
                population_size=33,
                maxsize=25,
                verbosity=0,
                progress=False,
                random_state=0,
            )
            model.fit(X, y, variable_names=["x1", "x2"])

            best_expr = model.sympy()
            expression = str(best_expr)
            predictions = model.predict(X)
            return expression, np.asarray(predictions, dtype=float)
        except Exception:
            return None, None

    def _fit_linear_baseline(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0].astype(float, copy=False)
        x2 = X[:, 1].astype(float, copy=False)
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except np.linalg.LinAlgError:
            coeffs = np.zeros(3, dtype=float)
        a, b, c = coeffs
        expression = f"({a:.10f})*x1 + ({b:.10f})*x2 + ({c:.10f})"
        predictions = A @ coeffs
        return expression, predictions

    def _fit_radial_model(self, X: np.ndarray, y: np.ndarray):
        try:
            rng = np.random.default_rng(0)

            x1 = X[:, 0].astype(float, copy=False)
            x2 = X[:, 1].astype(float, copy=False)
            r = np.sqrt(x1 * x1 + x2 * x2)

            n = y.shape[0]
            if n > 8000:
                idx = rng.choice(n, size=8000, replace=False)
            else:
                idx = np.arange(n)

            r_sub = r[idx]
            y_sub = y[idx]

            dA = 4  # degree of amplitude polynomial
            n_amp = dA + 1

            y_scale = float(np.max(np.abs(y_sub))) if y_sub.size > 0 else 1.0
            if y_scale <= 0:
                y_scale = 1.0

            amp_bound = 10.0 * y_scale
            c0_bound = 10.0 * y_scale
            b0_bound = 50.0
            b1_bound = 50.0
            b2_bound = 20.0

            # Frequency candidates for initialization
            freq_candidates = np.array(
                [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0,
                 6.0, 7.0, 8.0, 9.0, 10.0, 12.0,
                 15.0, 20.0, 25.0, 30.0],
                dtype=float,
            )

            best_ai_freq = []
            if r_sub.size > 0:
                for freq in freq_candidates:
                    sinBr = np.sin(freq * r_sub)
                    cols = [(r_sub ** i) * sinBr for i in range(n_amp)]
                    cols.append(np.ones_like(r_sub))
                    A_mat = np.column_stack(cols)
                    try:
                        coeffs, _, _, _ = np.linalg.lstsq(A_mat, y_sub, rcond=None)
                    except np.linalg.LinAlgError:
                        continue
                    ai = coeffs[:n_amp]
                    c0_init = coeffs[-1]
                    y_hat = A_mat @ coeffs
                    mse = float(np.mean((y_hat - y_sub) ** 2))
                    best_ai_freq.append((mse, freq, ai, c0_init))

            if not best_ai_freq:
                # Fallback directly to linear baseline if initialization fails
                return self._fit_linear_baseline(X, y)

            best_ai_freq.sort(key=lambda t: t[0])
            num_inits_from_freq = min(3, len(best_ai_freq))

            # Precompute powers of r_sub for optimization
            powers = np.column_stack([r_sub ** i for i in range(n_amp)])
            r_sub2 = r_sub ** 2

            def optimize_from_init(p0):
                p = p0.astype(float).copy()
                m_t = np.zeros_like(p)
                v_t = np.zeros_like(p)

                N = y_sub.size
                if N <= 4000:
                    n_steps = 600
                    lr = 1e-3
                else:
                    n_steps = 450
                    lr = 8e-4

                beta1 = 0.9
                beta2 = 0.999
                eps = 1e-8

                best_loss = np.inf
                best_p = p.copy()

                for t in range(1, n_steps + 1):
                    ai = p[:n_amp]
                    b0 = p[n_amp]
                    b1 = p[n_amp + 1]
                    b2 = p[n_amp + 2]
                    c0 = p[n_amp + 3]

                    A_val = powers @ ai
                    B_val = b0 + b1 * r_sub + b2 * r_sub2
                    sinB = np.sin(B_val)
                    cosB = np.cos(B_val)

                    y_pred = A_val * sinB + c0
                    res = y_pred - y_sub
                    loss = float(np.mean(res * res))

                    if loss < best_loss:
                        best_loss = loss
                        best_p = p.copy()

                    # Gradients
                    tmp = res * sinB
                    grad_ai = 2.0 * (powers.T @ tmp) / N

                    common = A_val * cosB
                    grad_b0 = 2.0 * np.mean(res * common)
                    grad_b1 = 2.0 * np.mean(res * common * r_sub)
                    grad_b2 = 2.0 * np.mean(res * common * r_sub2)
                    grad_c0 = 2.0 * np.mean(res)

                    grad = np.concatenate(
                        [grad_ai, np.array([grad_b0, grad_b1, grad_b2, grad_c0])]
                    )
                    grad = np.clip(grad, -1e3, 1e3)

                    m_t = beta1 * m_t + (1.0 - beta1) * grad
                    v_t = beta2 * v_t + (1.0 - beta2) * (grad * grad)
                    m_hat = m_t / (1.0 - beta1 ** t)
                    v_hat = v_t / (1.0 - beta2 ** t)
                    p -= lr * m_hat / (np.sqrt(v_hat) + eps)

                    # Parameter clipping
                    p[:n_amp] = np.clip(p[:n_amp], -amp_bound, amp_bound)
                    p[n_amp] = np.clip(p[n_amp], -b0_bound, b0_bound)
                    p[n_amp + 1] = np.clip(p[n_amp + 1], -b1_bound, b1_bound)
                    p[n_amp + 2] = np.clip(p[n_amp + 2], -b2_bound, b2_bound)
                    p[n_amp + 3] = np.clip(p[n_amp + 3], -c0_bound, c0_bound)

                return best_p, best_loss

            init_params_list = []

            # Inits from best frequencies
            for k in range(num_inits_from_freq):
                _, freq, ai_init, c0_init = best_ai_freq[k]
                ai_clipped = np.clip(ai_init, -amp_bound, amp_bound)
                c0_clipped = float(np.clip(c0_init, -c0_bound, c0_bound))
                b0_init = 0.0
                b1_init = float(freq)
                b2_init = 0.0
                p0 = np.concatenate(
                    [ai_clipped, np.array([b0_init, b1_init, b2_init, c0_clipped])]
                )
                init_params_list.append(p0)

            # Additional random initializations
            for _ in range(2):
                ai_rand = rng.normal(scale=0.5 * y_scale, size=n_amp)
                b0_rand = rng.uniform(-np.pi, np.pi)
                b1_rand = rng.uniform(0.5, 30.0)
                b2_rand = rng.uniform(-5.0, 5.0)
                c0_rand = float(np.mean(y_sub))
                p0 = np.concatenate(
                    [
                        ai_rand,
                        np.array([b0_rand, b1_rand, b2_rand, c0_rand], dtype=float),
                    ]
                )
                init_params_list.append(p0)

            best_overall_p = None
            best_overall_loss = np.inf

            for p0 in init_params_list:
                p_opt, loss_opt = optimize_from_init(p0)
                if loss_opt < best_overall_loss:
                    best_overall_loss = loss_opt
                    best_overall_p = p_opt

            if best_overall_p is None:
                return self._fit_linear_baseline(X, y)

            ai_best = best_overall_p[:n_amp]
            b0_best = best_overall_p[n_amp]
            b1_best = best_overall_p[n_amp + 1]
            b2_best = best_overall_p[n_amp + 2]
            c0_best = best_overall_p[n_amp + 3]

            # Build expression string
            r_expr = "(x1**2 + x2**2)**0.5"
            tol_coef = 1e-6

            # Amplitude polynomial
            amp_terms = []
            for i, a in enumerate(ai_best):
                if abs(a) < tol_coef:
                    continue
                if i == 0:
                    term = f"({a:.10f})"
                elif i == 1:
                    term = f"({a:.10f})*{r_expr}"
                else:
                    term = f"({a:.10f})*({r_expr}**{i})"
                amp_terms.append(term)

            if not amp_terms:
                A_expr = "0.0"
            elif len(amp_terms) == 1:
                A_expr = amp_terms[0]
            else:
                A_expr = "(" + " + ".join(amp_terms) + ")"

            # Phase polynomial
            phase_terms = []
            if abs(b0_best) >= tol_coef:
                phase_terms.append(f"({b0_best:.10f})")
            if abs(b1_best) >= tol_coef:
                phase_terms.append(f"({b1_best:.10f})*{r_expr}")
            if abs(b2_best) >= tol_coef:
                phase_terms.append(f"({b2_best:.10f})*({r_expr}**2)")
            if not phase_terms:
                B_expr = "0.0"
            elif len(phase_terms) == 1:
                B_expr = phase_terms[0]
            else:
                B_expr = "(" + " + ".join(phase_terms) + ")"

            # Constant offset
            if abs(c0_best) < tol_coef:
                C_expr = ""
            else:
                C_expr = f" + ({c0_best:.10f})"

            expression = f"{A_expr}*sin({B_expr}){C_expr}"

            # Compute predictions on full data
            r_full = r
            A_full = np.zeros_like(r_full)
            for i, a in enumerate(ai_best):
                if abs(a) < tol_coef:
                    continue
                if i == 0:
                    A_full += a
                else:
                    A_full += a * (r_full ** i)
            B_full = b0_best + b1_best * r_full + b2_best * (r_full ** 2)
            y_pred_full = A_full * np.sin(B_full) + c0_best

            return expression, y_pred_full
        except Exception:
            return self._fit_linear_baseline(X, y)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        expr, preds = self._fit_with_pysr(X, y)
        if expr is None:
            expr, preds = self._fit_radial_model(X, y)

        result = {
            "expression": expr,
            "predictions": preds.tolist() if preds is not None else None,
            "details": {},
        }
        return result
