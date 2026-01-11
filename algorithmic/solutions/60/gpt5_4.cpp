#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using ld = long double;

static const ll BOX = 100000;
static const ll X0 = 40000;
static const ll Y0 = 10000;
static const ld EPS = 1e-6L;

bool isPerfectSquareLL(ll n, ll &root) {
    if (n < 0) return false;
    ld r = sqrt((ld)n);
    ll ri = (ll)llround(r);
    if (ri < 0) ri = 0;
    while (ri * ri > n) --ri;
    while ((ri + 1) * (ri + 1) <= n) ++ri;
    if (ri * ri == n) {
        root = ri;
        return true;
    }
    return false;
}

ld predictR3(ll x, ll y, ll r) {
    // Compute overlap length on segment from (60000,60000) to (80000,80000) along line x=y
    // t parameter is coordinate t for point (t,t); physical length is sqrt(2)*(delta t)
    // Feasible t interval of circle on line:
    // From derivation: 2*(t - t0)^2 + (x - y)^2 / 2 <= r^2
    // => (t - t0)^2 <= (r^2 - (x - y)^2 / 2) / 2
    // Let L = sqrt(max(0, (r^2 - (x - y)^2 / 2) / 2))
    ld t0 = ((ld)x + (ld)y) / 2.0L;
    ld z = (ld)(x - y);
    ld val = (ld)r * (ld)r - (z * z) / 2.0L;
    if (val <= 0) return 0.0L;
    ld L = sqrt(val / 2.0L);
    ld a = 60000.0L, b = 80000.0L;
    ld left = max(a, t0 - L);
    ld right = min(b, t0 + L);
    if (right <= left) return 0.0L;
    ld tlen = right - left;
    ld seglen = tlen * M_SQRT2; // sqrt(2)
    return seglen;
}

vector<pair<ll,ll>> candidates_from_K(ll K) {
    // From R1>0: K = r^2 - (x - X0)^2 = (r - dx)(r + dx) where dx = |x - X0|, dx <= r
    // Factorize K into s * t with same parity. Then r=(s+t)/2, dx=(t-s)/2.
    vector<pair<ll,ll>> res; // (x, r)
    if (K <= 0) return res;
    ll limit = (ll)floor(sqrt((ld)K));
    set<pair<ll,ll>> seen;
    for (ll d = 1; d <= limit; ++d) {
        if (K % d != 0) continue;
        ll s = d, t = K / d;
        if (((s ^ t) & 1LL) != 0) continue; // parity mismatch
        ll r = (s + t) / 2;
        ll dx = (t - s) / 2;
        if (r < 0 || dx < 0) continue;
        if (dx > r) continue;
        if (r < 100 || r > 50000) continue;
        // x candidates
        ll x1 = X0 - dx;
        ll x2 = X0 + dx;
        if (x1 >= 0 && x1 <= (ll)BOX && r <= x1 && x1 <= (ll)BOX - r) {
            if (!seen.count({x1, r})) {
                res.push_back({x1, r});
                seen.insert({x1, r});
            }
        }
        if (dx != 0 && x2 >= 0 && x2 <= (ll)BOX && r <= x2 && x2 <= (ll)BOX - r) {
            if (!seen.count({x2, r})) {
                res.push_back({x2, r});
                seen.insert({x2, r});
            }
        }
    }
    return res;
}

vector<pair<ll,ll>> candidates_from_L(ll L) {
    // From R2>0: L = r^2 - (y - Y0)^2 = (r - dy)(r + dy), dy=|y - Y0| <= r
    // Similar to above, produce (y, r)
    vector<pair<ll,ll>> res;
    if (L <= 0) return res;
    ll limit = (ll)floor(sqrt((ld)L));
    set<pair<ll,ll>> seen;
    for (ll d = 1; d <= limit; ++d) {
        if (L % d != 0) continue;
        ll s = d, t = L / d;
        if (((s ^ t) & 1LL) != 0) continue;
        ll r = (s + t) / 2;
        ll dy = (t - s) / 2;
        if (r < 0 || dy < 0) continue;
        if (dy > r) continue;
        if (r < 100 || r > 50000) continue;
        // y candidates
        ll y1 = Y0 - dy;
        ll y2 = Y0 + dy;
        if (y1 >= 0 && y1 <= (ll)BOX && r <= y1 && y1 <= (ll)BOX - r) {
            if (!seen.count({y1, r})) {
                res.push_back({y1, r});
                seen.insert({y1, r});
            }
        }
        if (dy != 0 && y2 >= 0 && y2 <= (ll)BOX && r <= y2 && y2 <= (ll)BOX - r) {
            if (!seen.count({y2, r})) {
                res.push_back({y2, r});
                seen.insert({y2, r});
            }
        }
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    ld R1, R2, R3;
    if (!(cin >> R1)) {
        return 0;
    }
    if (!(cin >> R2)) return 0;
    if (!(cin >> R3)) return 0;

    bool vpos = R1 > EPS;
    bool hpos = R2 > EPS;

    ll K = 0, L = 0;
    if (vpos) {
        ld temp = (R1 * R1) / 4.0L;
        K = (ll)llround(temp);
    }
    if (hpos) {
        ld temp = (R2 * R2) / 4.0L;
        L = (ll)llround(temp);
    }

    vector<tuple<ll,ll,ll>> candidates; // (x, y, r)

    if (vpos) {
        auto xr = candidates_from_K(K);
        if (hpos) {
            // Use exact L to determine y
            for (auto [x, r] : xr) {
                ll diff = (ll)r * (ll)r - L;
                ll dy;
                if (!isPerfectSquareLL(diff, dy)) continue;
                // optional: ensure |y - Y0| <= r
                ll y1 = Y0 - dy, y2 = Y0 + dy;
                if (y1 >= (ll)r && y1 <= (ll)BOX - r) candidates.emplace_back(x, y1, r);
                if (dy != 0 && y2 >= (ll)r && y2 <= (ll)BOX - r) candidates.emplace_back(x, y2, r);
            }
        } else {
            // R2 == 0: only inequality |y - Y0| >= r
            // For each (x,r) candidate, scan y over allowed integers
            // y in [r, BOX - r], and (y <= Y0 - r) or (y >= Y0 + r)
            for (auto [x, r] : xr) {
                ll y_min = r;
                ll y_max = BOX - r;
                // Left range: [y_min, min(y_max, Y0 - r)]
                ll left_end = min(y_max, Y0 - r);
                // Right range: [max(y_min, Y0 + r), y_max]
                ll right_begin = max(y_min, Y0 + r);
                // Compute predicted R3 for potential y values; match with tolerance
                // Use tolerance a bit looser
                ld tol = 1e-4L;
                if (left_end >= y_min) {
                    for (ll y = y_min; y <= left_end; ++y) {
                        ld pr = predictR3(x, y, r);
                        if (fabsl(pr - R3) <= tol) {
                            candidates.emplace_back(x, y, r);
                            // Might be multiple; keep searching to collect all
                        }
                    }
                }
                if (y_max >= right_begin) {
                    for (ll y = right_begin; y <= y_max; ++y) {
                        ld pr = predictR3(x, y, r);
                        if (fabsl(pr - R3) <= tol) {
                            candidates.emplace_back(x, y, r);
                        }
                    }
                }
            }
        }
    } else if (hpos) {
        // R1 == 0 but R2 > 0: symmetric handling
        auto yr = candidates_from_L(L);
        for (auto [y, r] : yr) {
            // From |x - X0|^2 = r^2 - K; but K unknown since R1==0
            // However, R1==0 implies |x - X0| >= r (no intersection)
            // We will scan x over allowed integers satisfying |x - X0| >= r
            ll x_min = r;
            ll x_max = BOX - r;
            ll left_end = min(x_max, X0 - r);
            ll right_begin = max(x_min, X0 + r);
            ld tol = 1e-4L;
            if (left_end >= x_min) {
                for (ll x = x_min; x <= left_end; ++x) {
                    ld pr = predictR3(x, y, r);
                    if (fabsl(pr - R3) <= tol) {
                        candidates.emplace_back(x, y, r);
                    }
                }
            }
            if (x_max >= right_begin) {
                for (ll x = right_begin; x <= x_max; ++x) {
                    ld pr = predictR3(x, y, r);
                    if (fabsl(pr - R3) <= tol) {
                        candidates.emplace_back(x, y, r);
                    }
                }
            }
        }
    } else {
        // Both R1 and R2 are zero: insufficient information in this offline adaptation.
        // As a fallback, try scanning all possible r (100..50000), and scan x,y subject to |x-X0|>=r, |y-Y0|>=r and boundaries, and match R3.
        // This is heavy; we will try to prune by using R3 to restrict.
        // We'll implement a limited search: iterate r and scan possible x,y ranges narrowed by matching R3 roughly.
        ld tol = 1e-4L;
        for (ll r = 100; r <= 50000; ++r) {
            // Quick prune: R3 cannot exceed min(segment length, infinite chord length).
            // segment length is 20000*sqrt(2)
            ld max_seg = 20000.0L * M_SQRT2;
            // To possibly produce R3 > 0, the circle must intersect the line x=y.
            // But we can't quickly check; proceed.
            // Scan x in allowed ranges with |x - X0| >= r
            ll x_min = r, x_max = BOX - r;
            ll xl_end = min(x_max, X0 - r);
            ll xr_begin = max(x_min, X0 + r);
            // Similarly y must satisfy |y - Y0| >= r
            ll y_min = r, y_max = BOX - r;
            ll yl_end = min(y_max, Y0 - r);
            ll yr_begin = max(y_min, Y0 + r);
            // We'll coarsely sample to reduce complexity
            // But since this branch is unlikely, we can try a small coarse-to-fine search:
            vector<ll> xs, ys;
            if (xl_end >= x_min) { for (ll x = x_min; x <= xl_end; ++x) xs.push_back(x); }
            if (x_max >= xr_begin) { for (ll x = xr_begin; x <= x_max; ++x) xs.push_back(x); }
            if (yl_end >= y_min) { for (ll y = y_min; y <= yl_end; ++y) ys.push_back(y); }
            if (y_max >= yr_begin) { for (ll y = yr_begin; y <= y_max; ++y) ys.push_back(y); }
            for (ll x : xs) {
                for (ll y : ys) {
                    ld pr = predictR3(x, y, r);
                    if (fabsl(pr - R3) <= tol) {
                        candidates.emplace_back(x, y, r);
                        if (candidates.size() > 1000) break;
                    }
                }
                if (candidates.size() > 1000) break;
            }
            if (candidates.size() > 0) break;
        }
    }

    // Now, from candidates, select the one that matches R1 and R2 (if positive) more precisely.
    ll best_x = -1, best_y = -1, best_r = -1;
    ld best_err = 1e100L;
    for (auto [x, y, r] : candidates) {
        // Validate boundary constraints
        if (!(r >= 100 && r <= 50000)) continue;
        if (!(x >= r && x <= (ll)BOX - r)) continue;
        if (!(y >= r && y <= (ll)BOX - r)) continue;

        bool ok = true;
        if (vpos) {
            ld dx = (ld)llabs(x - X0);
            ld pred = 2.0L * sqrt(max<ld>(0.0L, (ld)r * (ld)r - dx * dx));
            if (fabsl(pred - R1) > 1e-4L) ok = false;
        } else {
            // R1 == 0 -> ensure |x - X0| >= r (no intersection)
            if (llabs(x - X0) < r) ok = false;
        }
        if (!ok) continue;

        if (hpos) {
            ld dy = (ld)llabs(y - Y0);
            ld pred = 2.0L * sqrt(max<ld>(0.0L, (ld)r * (ld)r - dy * dy));
            if (fabsl(pred - R2) > 1e-4L) ok = false;
        } else {
            if (llabs(y - Y0) < r) ok = false;
        }
        if (!ok) continue;

        ld pr3 = predictR3(x, y, r);
        ld err = fabsl(pr3 - R3);
        if (err < best_err) {
            best_err = err;
            best_x = x;
            best_y = y;
            best_r = r;
        }
    }

    if (best_x == -1) {
        // As a fallback, try to construct via both chords positive diophantine if applicable
        if (vpos && hpos) {
            // dx^2 - dy^2 = Δ where Δ = L - K
            ll Delta = L - K;
            ll S = llabs(Delta);
            vector<pair<ll,ll>> cand_dxdy;
            if (S == 0) {
                // dx = dy; try r from sqrt(K) up to limit
                for (ll r = 100; r <= 50000; ++r) {
                    ll dx2 = (ll)r * (ll)r - K;
                    ll dy2 = (ll)r * (ll)r - L;
                    if (dx2 < 0 || dy2 < 0) continue;
                    ll dx, dy;
                    if (!isPerfectSquareLL(dx2, dx)) continue;
                    if (!isPerfectSquareLL(dy2, dy)) continue;
                    if (dx != dy) continue;
                    // test signs
                    for (int sx : {-1, 1}) {
                        for (int sy : {-1, 1}) {
                            ll x = X0 + sx * dx;
                            ll y = Y0 + sy * dy;
                            if (x < r || x > BOX - r) continue;
                            if (y < r || y > BOX - r) continue;
                            ld pr3 = predictR3(x, y, r);
                            ld err = fabsl(pr3 - R3);
                            if (err < best_err) {
                                best_err = err;
                                best_x = x; best_y = y; best_r = r;
                            }
                        }
                    }
                }
            } else {
                // factor S = |Δ| into p*q with p = sign(Δ)*d, q = S/d
                for (ll d = 1; d * d <= S; ++d) {
                    if (S % d != 0) continue;
                    for (int take = 0; take < 2; ++take) {
                        ll q = (take == 0) ? (S / d) : d;
                        ll p_abs = (take == 0) ? d : (S / d);
                        ll p = (Delta >= 0 ? p_abs : -p_abs);
                        // parity check
                        if (((q ^ llabs(p)) & 1LL) != 0) continue;
                        ll dx = (q + p) / 2;
                        ll dy = (q - p) / 2;
                        if (dx < 0 || dy < 0) continue;
                        // r^2 = dx^2 + K must be a perfect square
                        ll r2 = dx * dx + K;
                        ll r;
                        if (!isPerfectSquareLL(r2, r)) continue;
                        if (r < 100 || r > 50000) continue;
                        for (int sx : {-1, 1}) {
                            for (int sy : {-1, 1}) {
                                ll x = X0 + sx * dx;
                                ll y = Y0 + sy * dy;
                                if (x < r || x > BOX - r) continue;
                                if (y < r || y > BOX - r) continue;
                                ld pr3 = predictR3(x, y, r);
                                ld err = fabsl(pr3 - R3);
                                if (err < best_err) {
                                    best_err = err;
                                    best_x = x; best_y = y; best_r = r;
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (best_x == -1) {
        // As last resort, pick some default (should not happen in valid testcases)
        // We'll try a coarse scan for r from 100..50000 with coarse steps
        ld tol = 1e-4L;
        for (ll r = 100; r <= 50000 && best_x == -1; r += 100) {
            for (ll x = r; x <= BOX - r && best_x == -1; x += 100) {
                // Check R1 and R2 constraints quickly
                bool ok1 = true, ok2 = true;
                if (vpos) {
                    ld dx = (ld)llabs(x - X0);
                    ld pred = 2.0L * sqrt(max<ld>(0.0L, (ld)r * (ld)r - dx * dx));
                    if (fabsl(pred - R1) > 1e-2L) ok1 = false;
                } else {
                    if (llabs(x - X0) < r) ok1 = false;
                }
                if (!ok1) continue;
                for (ll y = r; y <= BOX - r && best_x == -1; y += 100) {
                    if (hpos) {
                        ld dy = (ld)llabs(y - Y0);
                        ld pred = 2.0L * sqrt(max<ld>(0.0L, (ld)r * (ld)r - dy * dy));
                        if (fabsl(pred - R2) > 1e-2L) continue;
                    } else {
                        if (llabs(y - Y0) < r) continue;
                    }
                    ld pr3 = predictR3(x, y, r);
                    if (fabsl(pr3 - R3) <= 1e-2L) {
                        best_x = x; best_y = y; best_r = r;
                    }
                }
            }
        }
        if (best_x == -1) {
            // Fallback: assume some default to avoid no output
            best_x = max(100LL, min(BOX - 100LL, X0));
            best_y = max(100LL, min(BOX - 100LL, Y0));
            best_r = 100;
        }
    }

    cout << "answer " << best_x << " " << best_y << " " << best_r << "\n";
    return 0;
}