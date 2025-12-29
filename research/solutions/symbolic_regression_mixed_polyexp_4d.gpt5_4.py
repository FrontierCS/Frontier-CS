import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        n, d = X.shape
        if d != 4:
            raise ValueError("X must have 4 columns for x1, x2, x3, x4.")
        # Standardization parameters
        mu = X.mean(axis=0)
        sigma = X.std(axis=0)
        sigma = np.where(sigma < 1e-12, 1.0, sigma)

        Z = (X - mu) / sigma

        # Feature builders for Z-space
        pairs = [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
        def build_plin_z(Z):
            n = Z.shape[0]
            return np.column_stack([np.ones(n), Z])

        def build_pfull_z(Z):
            n = Z.shape[0]
            z1, z2, z3, z4 = Z[:,0], Z[:,1], Z[:,2], Z[:,3]
            cross = [Z[:,i]*Z[:,j] for (i,j) in pairs]
            squares = [Z[:,i]**2 for i in range(4)]
            return np.column_stack([np.ones(n), z1, z2, z3, z4] + cross + squares)

        def build_qm_z(Z):
            n = Z.shape[0]
            squares = [Z[:,i]**2 for i in range(4)]
            cross = [Z[:,i]*Z[:,j] for (i,j) in pairs]
            return np.column_stack(squares + cross)

        P_lin_z = build_plin_z(Z)      # shape (n,5) -> [1, z1..z4]
        P_full_z = build_pfull_z(Z)    # shape (n,15) -> [1, z1..z4, z1z2..z3z4, z1^2..z4^2]
        Qm_z = build_qm_z(Z)           # shape (n,10) -> [z1^2..z4^2, z1z2..z3z4]

        # Baseline least squares for A (linear part)
        try:
            a0 = np.linalg.lstsq(P_lin_z, y, rcond=None)[0]
        except Exception:
            a0 = np.zeros(P_lin_z.shape[1])
        base_pred = P_lin_z @ a0
        base_mse = float(np.mean((base_pred - y)**2))

        # Initialize B and D (exponential components)
        r0 = y - base_pred
        try:
            b0 = np.linalg.lstsq(P_full_z, r0, rcond=None)[0]
        except Exception:
            b0 = np.zeros(P_full_z.shape[1])
        d0 = np.full(Qm_z.shape[1], 0.1)

        # Training: minimize MSE of A + B*exp(-Q)
        def train_model(P_lin, P_full, Qm, y, restarts=6, steps=800, seed=42):
            rng = np.random.default_rng(seed)
            n = y.shape[0]
            best = {
                "a": a0.copy(),
                "b": b0.copy(),
                "d": d0.copy(),
                "mse": base_mse
            }
            # Hyperparameters
            beta1, beta2 = 0.9, 0.999
            eps = 1e-8
            lam_a = 1e-6
            lam_b = 1e-6
            lam_d = 1e-6
            alpha_neg = 1e-3  # penalty for negative d entries
            gamma_qneg = 1e-4  # penalty for negative Q(x) across dataset
            # Learning rates
            lr_a0 = 0.03
            lr_b0 = 0.03
            lr_d0 = 0.01

            for r in range(restarts):
                a = a0.copy()
                b = b0.copy()
                d = d0.copy()
                # Add small noise to break symmetry
                a += 0.01 * rng.standard_normal(size=a.shape)
                b += 0.01 * rng.standard_normal(size=b.shape)
                d += 0.01 * rng.standard_normal(size=d.shape)

                ma = np.zeros_like(a)
                va = np.zeros_like(a)
                mb = np.zeros_like(b)
                vb = np.zeros_like(b)
                md = np.zeros_like(d)
                vd = np.zeros_like(d)

                lr_a, lr_b, lr_d = lr_a0, lr_b0, lr_d0

                best_local_mse = float('inf')
                no_improve = 0
                patience = max(200, steps // 3)

                for t in range(1, steps + 1):
                    # Optional lr decay
                    if t % 200 == 0:
                        lr_a *= 0.8
                        lr_b *= 0.8
                        lr_d *= 0.8

                    Tq = Qm @ d  # shape (n,)
                    # Clip to avoid overflow in exp during training
                    Tq_clipped = np.clip(Tq, -60.0, 60.0)
                    E = np.exp(-Tq_clipped)  # shape (n,)

                    A = P_lin @ a
                    B = P_full @ b
                    f = A + B * E
                    rvec = f - y

                    mse = float(np.mean(rvec**2))

                    if mse < best_local_mse - 1e-12:
                        best_local_mse = mse
                        no_improve = 0
                    else:
                        no_improve += 1

                    if mse < best["mse"] - 1e-12:
                        best["mse"] = mse
                        best["a"] = a.copy()
                        best["b"] = b.copy()
                        best["d"] = d.copy()

                    if no_improve > patience:
                        break

                    # Gradients
                    # dL/da
                    ga = (P_lin.T @ rvec) / n + lam_a * a
                    # dL/db
                    gb = (P_full.T @ (rvec * E)) / n + lam_b * b
                    # dL/dd
                    # Using un-clipped Tq for penalty only; but gradient w.r.t exp uses clipped E; approximate
                    gd = - (Qm.T @ (rvec * B * E)) / n + lam_d * d

                    # Penalty: discourage negative d (promote positive)
                    gd += 2.0 * alpha_neg * np.where(d < 0.0, d, 0.0)

                    # Penalty: discourage negative Q over data (Gaussian-like)
                    # gradient of mean(min(Tq, 0)^2) wrt d = (2/n) * sum_{s with Tq_s<0} Tq_s * Qm_s
                    mask_neg = Tq < 0.0
                    if np.any(mask_neg):
                        Tneg = Tq[mask_neg]
                        Qneg = Qm[mask_neg, :]
                        gd += (2.0 * gamma_qneg / n) * (Qneg.T @ Tneg)

                    # Adam updates
                    ma = beta1 * ma + (1 - beta1) * ga
                    va = beta2 * va + (1 - beta2) * (ga * ga)
                    mb = beta1 * mb + (1 - beta1) * gb
                    vb = beta2 * vb + (1 - beta2) * (gb * gb)
                    md = beta1 * md + (1 - beta1) * gd
                    vd = beta2 * vd + (1 - beta2) * (gd * gd)

                    ma_hat = ma / (1 - beta1**t)
                    va_hat = va / (1 - beta2**t)
                    mb_hat = mb / (1 - beta1**t)
                    vb_hat = vb / (1 - beta2**t)
                    md_hat = md / (1 - beta1**t)
                    vd_hat = vd / (1 - beta2**t)

                    a = a - lr_a * ma_hat / (np.sqrt(va_hat) + eps)
                    b = b - lr_b * mb_hat / (np.sqrt(vb_hat) + eps)
                    d = d - lr_d * md_hat / (np.sqrt(vd_hat) + eps)

                # End steps
            # End restarts
            return best["a"], best["b"], best["d"], best["mse"]

        a_z, b_z, d_z, mse_tr = train_model(P_lin_z, P_full_z, Qm_z, y, restarts=6, steps=900, seed=42)

        # Map trained parameters from z-space to x-space for a compact expression
        # Basis orders:
        # For polynomial degree 2 in x:
        # idx: 0->1, 1->x1, 2->x2, 3->x3, 4->x4, 5->x1x2,6->x1x3,7->x1x4,8->x2x3,9->x2x4,10->x3x4, 11->x1^2,12->x2^2,13->x3^2,14->x4^2
        def map_Az_to_Ax(a_z, mu, sigma):
            ax = np.zeros(5, dtype=float)
            ax[0] += a_z[0]
            for i in range(4):
                s = sigma[i]
                m = mu[i]
                ai = a_z[1 + i]
                ax[0] += ai * (-m / s)
                ax[1 + i] += ai * (1.0 / s)
            return ax

        # Map B_z (degree 2 in z) to B_x (degree 2 in x)
        def map_Bz_to_Bx(b_z, mu, sigma):
            bx = np.zeros(15, dtype=float)
            # constant term
            bx[0] += b_z[0]
            # linear terms
            for i in range(4):
                s = sigma[i]; m = mu[i]; coeff = b_z[1 + i]
                bx[0] += coeff * (-m / s)
                bx[1 + i] += coeff * (1.0 / s)
            # cross terms z_i*z_j
            cross_base = 5
            for idx, (i, j) in enumerate(pairs):
                coeff = b_z[cross_base + idx]
                si, sj = sigma[i], sigma[j]
                mi, mj = mu[i], mu[j]
                # constant
                bx[0] += coeff * (mi * mj / (si * sj))
                # linear x_i
                bx[1 + i] += coeff * (-mj / (si * sj))
                # linear x_j
                bx[1 + j] += coeff * (-mi / (si * sj))
                # pair x_i*x_j
                bx[5 + idx] += coeff * (1.0 / (si * sj))
            # squares z_i^2
            sq_base = 11
            for i in range(4):
                coeff = b_z[sq_base + i]
                si = sigma[i]; mi = mu[i]
                bx[0] += coeff * ((mi**2) / (si**2))
                bx[1 + i] += coeff * ((-2.0 * mi) / (si**2))
                bx[11 + i] += coeff * (1.0 / (si**2))
            return bx

        # Map d_z (Q in z) to q_x (Q in x) with basis [1, x1..x4, x1x2.., x1^2..]
        def map_dz_to_qx(d_z, mu, sigma):
            qx = np.zeros(15, dtype=float)
            # squares z_i^2 (indices 0..3)
            for i in range(4):
                coeff = d_z[i]
                si = sigma[i]; mi = mu[i]
                qx[0] += coeff * ((mi**2) / (si**2))
                qx[1 + i] += coeff * ((-2.0 * mi) / (si**2))
                qx[11 + i] += coeff * (1.0 / (si**2))
            # cross z_i*z_j (indices 4..9)
            for idx, (i, j) in enumerate(pairs):
                coeff = d_z[4 + idx]
                si, sj = sigma[i], sigma[j]
                mi, mj = mu[i], mu[j]
                qx[0] += coeff * (mi * mj / (si * sj))
                qx[1 + i] += coeff * (-mj / (si * sj))
                qx[1 + j] += coeff * (-mi / (si * sj))
                qx[5 + idx] += coeff * (1.0 / (si * sj))
            return qx

        a_x = map_Az_to_Ax(a_z, mu, sigma)
        b_x = map_Bz_to_Bx(b_z, mu, sigma)
        q_x = map_dz_to_qx(d_z, mu, sigma)

        # Build predictions using x-space compact representation
        x1, x2, x3, x4 = X[:,0], X[:,1], X[:,2], X[:,3]

        # P_lin_x: [1, x1, x2, x3, x4]
        P_lin_x = np.column_stack([np.ones(n), x1, x2, x3, x4])

        # P_full_x: [1, x1..x4, x1x2..x3x4, x1^2..x4^2]
        cross_x = [x1*x2, x1*x3, x1*x4, x2*x3, x2*x4, x3*x4]
        squares_x = [x1**2, x2**2, x3**2, x4**2]
        P_full_x = np.column_stack([np.ones(n), x1, x2, x3, x4] + cross_x + squares_x)

        # Q_x features: [1, x1, x2, x3, x4, pairs(6), squares(4)]
        Qx = np.column_stack([np.ones(n), x1, x2, x3, x4] + cross_x + squares_x)
        Tq = Qx @ q_x
        # Clip extreme to avoid overflow in returned predictions (expression may overflow on evaluation engine, but predictions are just for convenience)
        Tq_clip = np.clip(Tq, -700.0, 700.0)
        E = np.exp(-Tq_clip)
        preds = (P_lin_x @ a_x) + (P_full_x @ b_x) * E

        # If model failed to improve over baseline, fallback to polynomial degree 2 only (no exp)
        if float(np.mean((preds - y)**2)) >= base_mse * 0.999:
            # Fit full quadratic polynomial in x directly
            try:
                # Build X_poly as P_full_x (degree 2) for y
                coef_poly, *_ = np.linalg.lstsq(P_full_x, y, rcond=None)
            except Exception:
                coef_poly = np.zeros(15, dtype=float)
                coef_poly[0] = np.mean(y)
            # Expression builder for polynomial only
            def poly_full_str(coefs):
                terms = []
                thr = 1e-12 * (1.0 + float(np.max(np.abs(coefs))))
                c0 = coefs[0]
                if abs(c0) > thr:
                    terms.append(f"({c0:.12g})")
                names = ["x1","x2","x3","x4"]
                for i in range(4):
                    ci = coefs[1+i]
                    if abs(ci) > thr:
                        terms.append(f"({ci:.12g})*{names[i]}")
                pair_names = [("x1","x2"),("x1","x3"),("x1","x4"),("x2","x3"),("x2","x4"),("x3","x4")]
                for idx, (u, v) in enumerate(pair_names):
                    ci = coefs[5+idx]
                    if abs(ci) > thr:
                        terms.append(f"({ci:.12g})*{u}*{v}")
                for i in range(4):
                    ci = coefs[11+i]
                    if abs(ci) > thr:
                        terms.append(f"({ci:.12g})*{names[i]}**2")
                if not terms:
                    return "0"
                return " + ".join(terms)
            expression = poly_full_str(coef_poly)
            predictions = (P_full_x @ coef_poly).tolist()
            return {
                "expression": expression,
                "predictions": predictions,
                "details": {}
            }

        # Build final expression string using x-space coefficients
        def poly_lin_str(ax):
            terms = []
            thr = 1e-12 * (1.0 + float(np.max(np.abs(ax))))
            c0 = ax[0]
            if abs(c0) > thr:
                terms.append(f"({c0:.12g})")
            names = ["x1","x2","x3","x4"]
            for i in range(4):
                ci = ax[1+i]
                if abs(ci) > thr:
                    terms.append(f"({ci:.12g})*{names[i]}")
            if not terms:
                return "0"
            return " + ".join(terms)

        def poly_full_str(bx):
            terms = []
            thr = 1e-12 * (1.0 + float(np.max(np.abs(bx))))
            c0 = bx[0]
            if abs(c0) > thr:
                terms.append(f"({c0:.12g})")
            names = ["x1","x2","x3","x4"]
            for i in range(4):
                ci = bx[1+i]
                if abs(ci) > thr:
                    terms.append(f"({ci:.12g})*{names[i]}")
            pair_names = [("x1","x2"),("x1","x3"),("x1","x4"),("x2","x3"),("x2","x4"),("x3","x4")]
            for idx, (u, v) in enumerate(pair_names):
                ci = bx[5+idx]
                if abs(ci) > thr:
                    terms.append(f"({ci:.12g})*{u}*{v}")
            for i in range(4):
                ci = bx[11+i]
                if abs(ci) > thr:
                    terms.append(f"({ci:.12g})*{names[i]}**2")
            if not terms:
                return "0"
            return " + ".join(terms)

        def q_str(qx):
            # qx basis: [1, x1, x2, x3, x4, pairs(6), squares(4)]
            terms = []
            thr = 1e-12 * (1.0 + float(np.max(np.abs(qx))))
            c0 = qx[0]
            if abs(c0) > thr:
                terms.append(f"({c0:.12g})")
            names = ["x1","x2","x3","x4"]
            for i in range(4):
                ci = qx[1+i]
                if abs(ci) > thr:
                    terms.append(f"({ci:.12g})*{names[i]}")
            pair_names = [("x1","x2"),("x1","x3"),("x1","x4"),("x2","x3"),("x2","x4"),("x3","x4")]
            for idx, (u, v) in enumerate(pair_names):
                ci = qx[5+idx]
                if abs(ci) > thr:
                    terms.append(f"({ci:.12g})*{u}*{v}")
            for i in range(4):
                ci = qx[11+i]
                if abs(ci) > thr:
                    terms.append(f"({ci:.12g})*{names[i]}**2")
            if not terms:
                return "0"
            return " + ".join(terms)

        A_str = poly_lin_str(a_x)
        B_str = poly_full_str(b_x)
        Q_str = q_str(q_x)

        if B_str.strip() == "0":
            expression = A_str
        else:
            expression = f"({A_str}) + ({B_str})*exp(-({Q_str}))"

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }