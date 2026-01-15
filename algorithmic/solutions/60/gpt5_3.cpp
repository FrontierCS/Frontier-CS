#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using ld = long double;

static const int BOX = 100000;
static const int LX = 40000; // vertical line x = 40000
static const int LY = 10000; // horizontal line y = 10000
static const int UA = 60000; // diag segment u start (u=x on y=x)
static const int UB = 80000; // diag segment u end
static const ld SQRT2 = sqrtl((ld)2.0);
static const ld EPS0 = 1e-9;
static const ld TOL = 1e-4;
static const ld TOL3 = 1e-3;

inline bool isZero(ld x) { return fabsl(x) <= 1e-7; }

static inline bool isPerfectSquareLL(long long x, long long &r) {
    if (x < 0) return false;
    long double sr = floorl(sqrtl((long double)x) + 0.5L);
    long long rr = (long long)sr;
    if (rr < 0) rr = 0;
    if ((long long)rr * (long long)rr == x) { r = rr; return true; }
    // Adjust around
    if ((rr+1) > 0 && (long long)(rr+1) * (long long)(rr+1) == x) { r = rr+1; return true; }
    if (rr>0 && (long long)(rr-1) * (long long)(rr-1) == x) { r = rr-1; return true; }
    return false;
}

static inline ld predL1(int x, int r) {
    ll dx = llabs((ll)x - (ll)LX);
    if (dx > r) return 0.0L;
    ld val = (ld)r*(ld)r - (ld)dx*(ld)dx;
    if (val < 0) val = 0;
    return 2.0L * sqrtl(val);
}
static inline ld predL2(int y, int r) {
    ll dy = llabs((ll)y - (ll)LY);
    if (dy > r) return 0.0L;
    ld val = (ld)r*(ld)r - (ld)dy*(ld)dy;
    if (val < 0) val = 0;
    return 2.0L * sqrtl(val);
}
static inline ld predL3(int x, int y, int r) {
    // diagonal segment from (60000,60000) to (80000,80000)
    // map to u coordinate: u = x = y on the line
    // chord half length along euclidean t = sqrt(r^2 - d^2), where d = |y - x| / sqrt(2)
    ld diff = fabsl((ld)y - (ld)x);
    ld d = diff / SQRT2;
    if (d > (ld)r + 1e-12L) return 0.0L;
    ld t = sqrtl(max((ld)0.0, (ld)r*(ld)r - d*d));
    ld u = ((ld)x + (ld)y) / 2.0L;
    ld h_u = t / SQRT2;
    ld lo1 = u - h_u, hi1 = u + h_u;
    ld lo2 = (ld)UA, hi2 = (ld)UB;
    ld ilo = max(lo1, lo2);
    ld ihi = min(hi1, hi2);
    ld lenU = ihi - ilo;
    if (lenU <= 0) return 0.0L;
    return SQRT2 * lenU;
}

// Generate candidate (r, x) pairs from L1>0 via factoring S1 near rounded (L1/2)^2
static vector<pair<int,int>> genCandidatesRX_fromL1(ld L1) {
    vector<pair<int,int>> out;
    if (!(L1 > 1e-7)) return out;
    ld half = L1 / 2.0L;
    long double Sapprox = half * half;
    long long Sbase = (long long) llround(Sapprox);
    set<pair<int,int>> seen; // (r,x)
    for (int delta = -2; delta <= 2; ++delta) {
        long long S = Sbase + delta;
        if (S < 0) continue;
        long long lim = (long long)floorl(sqrtl((long double)S) + 0.0000001L);
        for (long long v = 1; v <= lim; ++v) {
            if (S % v != 0) continue;
            long long u = S / v;
            // r = (u + v)/2 , d = (u - v)/2
            if (((u + v) & 1LL) != 0LL) continue;
            long long r = (u + v) / 2;
            long long d = (u - v) / 2;
            if (r < 0 || d < 0) continue;
            if (r > 100000) continue;
            // x candidates
            long long x1 = (long long)LX - d;
            long long x2 = (long long)LX + d;
            if (x1 >= 0 && x1 <= BOX && r >= 100 && r <= 100000 && r <= x1 && r <= (BOX - x1)) {
                if (!seen.count({(int)r, (int)x1})) {
                    seen.insert({(int)r, (int)x1});
                    out.emplace_back((int)r, (int)x1);
                }
            }
            if (x2 >= 0 && x2 <= BOX && r >= 100 && r <= 100000 && r <= x2 && r <= (BOX - x2)) {
                if (!seen.count({(int)r, (int)x2})) {
                    seen.insert({(int)r, (int)x2});
                    out.emplace_back((int)r, (int)x2);
                }
            }
        }
    }
    return out;
}

// Generate candidate (r, y) pairs from L2>0 via factoring S2 near rounded (L2/2)^2
static vector<pair<int,int>> genCandidatesRY_fromL2(ld L2) {
    vector<pair<int,int>> out;
    if (!(L2 > 1e-7)) return out;
    ld half = L2 / 2.0L;
    long double Sapprox = half * half;
    long long Sbase = (long long) llround(Sapprox);
    set<pair<int,int>> seen; // (r,y)
    for (int delta = -2; delta <= 2; ++delta) {
        long long S = Sbase + delta;
        if (S < 0) continue;
        long long lim = (long long)floorl(sqrtl((long double)S) + 0.0000001L);
        for (long long v = 1; v <= lim; ++v) {
            if (S % v != 0) continue;
            long long u = S / v;
            if (((u + v) & 1LL) != 0LL) continue;
            long long r = (u + v) / 2;
            long long d = (u - v) / 2;
            if (r < 0 || d < 0) continue;
            if (r > 100000) continue;
            long long y1 = (long long)LY - d;
            long long y2 = (long long)LY + d;
            if (y1 >= 0 && y1 <= BOX && r >= 100 && r <= 100000 && r <= y1 && r <= (BOX - y1)) {
                if (!seen.count({(int)r, (int)y1})) {
                    seen.insert({(int)r, (int)y1});
                    out.emplace_back((int)r, (int)y1);
                }
            }
            if (y2 >= 0 && y2 <= BOX && r >= 100 && r <= 100000 && r <= y2 && r <= (BOX - y2)) {
                if (!seen.count({(int)r, (int)y2})) {
                    seen.insert({(int)r, (int)y2});
                    out.emplace_back((int)r, (int)y2});
                }
            }
        }
    }
    return out;
}

// Using diagonal segment and known coordinate (kCoord as either x or y), generate candidate integer otherCoord values
static vector<int> genOtherCoordFromDiag(int r, int knownCoord, ld L3) {
    vector<int> res;
    set<int> added;
    ld rad2 = (ld)r * (ld)r;
    ld S = L3 / SQRT2;
    // Inside-case: L3 = 2*sqrt(r^2 - 2 t^2) -> t^2 = (r^2 - (L3^2)/4)/2
    ld val = rad2 - (L3 * L3) / 4.0L;
    if (val < 0 && fabsl(val) < 1e-7L) val = 0;
    if (val >= 0) {
        ld tAbs = sqrtl(val / 2.0L);
        // two t candidates
        for (int sgn = -1; sgn <= 1; sgn += 2) {
            ld t = sgn * tAbs;
            ld yD = (ld)knownCoord + 2.0L * t;
            // try rounding to nearest integer and neighbors
            for (int d = -1; d <= 1; ++d) {
                long long yi = llround(yD) + d;
                if (yi < 0 || yi > BOX) continue;
                int y = (int)yi;
                if (added.insert(y).second) res.push_back(y);
            }
        }
    }
    // Left-case: S = u - UA + h_u, with u = k + t
    // Solve: c = S + UA - k; t = ( c ± sqrt( r^2 - c^2 ) ) / 2
    {
        ld c = S + (ld)UA - (ld)knownCoord;
        ld T = rad2 - c * c;
        if (T < 0 && fabsl(T) < 1e-7L) T = 0;
        if (T >= 0) {
            ld root = sqrtl(T);
            ld t1 = (c + root) / 2.0L;
            ld t2 = (c - root) / 2.0L;
            ld ys[2] = {(ld)knownCoord + 2.0L * t1, (ld)knownCoord + 2.0L * t2};
            for (int i = 0; i < 2; ++i) {
                ld yD = ys[i];
                for (int d = -1; d <= 1; ++d) {
                    long long yi = llround(yD) + d;
                    if (yi < 0 || yi > BOX) continue;
                    int y = (int)yi;
                    if (added.insert(y).second) res.push_back(y);
                }
            }
        }
    }
    // Right-case: S = UB - u + h_u; c2 = S + k - UB; t = (-c2 ± sqrt(r^2 - c2^2))/2
    {
        ld c2 = S + (ld)knownCoord - (ld)UB;
        ld T = rad2 - c2 * c2;
        if (T < 0 && fabsl(T) < 1e-7L) T = 0;
        if (T >= 0) {
            ld root = sqrtl(T);
            ld t1 = (-c2 + root) / 2.0L;
            ld t2 = (-c2 - root) / 2.0L;
            ld ys[2] = {(ld)knownCoord + 2.0L * t1, (ld)knownCoord + 2.0L * t2};
            for (int i = 0; i < 2; ++i) {
                ld yD = ys[i];
                for (int d = -1; d <= 1; ++d) {
                    long long yi = llround(yD) + d;
                    if (yi < 0 || yi > BOX) continue;
                    int y = (int)yi;
                    if (added.insert(y).second) res.push_back(y);
                }
            }
        }
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    ld L1, L2, L3;
    if (!(cin >> L1)) return 0;
    if (!(cin >> L2)) return 0;
    if (!(cin >> L3)) return 0;

    vector<tuple<int,int,int>> answers; // (x,y,r)

    // Try case using L1>0
    if (L1 > 1e-7) {
        auto candRX = genCandidatesRX_fromL1(L1);
        // Precompute S2approx if needed
        ld h2 = L2 / 2.0L;
        long double S2approx = h2 * h2;
        long long S2base = (long long) llround(S2approx);
        for (auto [r, x] : candRX) {
            // Bound to ensure circle lies within in x direction
            if (!(r <= x && r <= (BOX - x))) continue;

            if (L2 > 1e-7) {
                // derive y via S2
                bool any = false;
                for (int delta = -2; delta <= 2; ++delta) {
                    long long S2cand = S2base + delta;
                    long long d2sq = (long long)r*(long long)r - S2cand;
                    if (d2sq < 0) continue;
                    long long d2;
                    if (!isPerfectSquareLL(d2sq, d2)) continue;
                    // two y candidates
                    long long y1 = (long long)LY - d2;
                    long long y2 = (long long)LY + d2;
                    long long ys[2] = {y1, y2};
                    for (int k = 0; k < 2; ++k) {
                        long long yll = ys[k];
                        if (yll < 0 || yll > BOX) continue;
                        int y = (int)yll;
                        if (!(r <= y && r <= (BOX - y))) continue;
                        ld l1p = predL1(x, r);
                        ld l2p = predL2(y, r);
                        ld l3p = predL3(x, y, r);
                        if (fabsl(l1p - L1) <= TOL && fabsl(l2p - L2) <= TOL && fabsl(l3p - L3) <= TOL3) {
                            answers.emplace_back(x, y, r);
                            any = true;
                        }
                    }
                }
                if (any) {
                    // do not break; collect all, then dedup and choose unique
                }
            } else {
                // L2 == 0: generate y candidates from diagonal
                auto ycands = genOtherCoordFromDiag(r, x, L3);
                for (int y : ycands) {
                    if (y < 0 || y > BOX) continue;
                    if (!(r <= y && r <= (BOX - y))) continue;
                    // L2 == 0 condition
                    ld l2p = predL2(y, r);
                    if (l2p > 1e-3L) continue;
                    ld l1p = predL1(x, r);
                    ld l3p = predL3(x, y, r);
                    if (fabsl(l1p - L1) <= TOL && fabsl(l3p - L3) <= TOL3) {
                        answers.emplace_back(x, y, r);
                    }
                }
            }
        }
    }

    // If not found yet, try using L2>0 and symmetrical approach (solve y then x from diagonal)
    if (answers.empty() && L2 > 1e-7) {
        auto candRY = genCandidatesRY_fromL2(L2);
        // Precompute S1approx if needed
        ld h1 = L1 / 2.0L;
        long double S1approx = h1 * h1;
        long long S1base = (long long) llround(S1approx);

        for (auto [r, y] : candRY) {
            if (!(r <= y && r <= (BOX - y))) continue;

            if (L1 > 1e-7) {
                // Derive x via S1
                bool any = false;
                for (int delta = -2; delta <= 2; ++delta) {
                    long long S1cand = S1base + delta;
                    long long d1sq = (long long)r*(long long)r - S1cand;
                    if (d1sq < 0) continue;
                    long long d1;
                    if (!isPerfectSquareLL(d1sq, d1)) continue;
                    long long x1 = (long long)LX - d1;
                    long long x2 = (long long)LX + d1;
                    long long xs[2] = {x1, x2};
                    for (int k = 0; k < 2; ++k) {
                        long long xll = xs[k];
                        if (xll < 0 || xll > BOX) continue;
                        int x = (int)xll;
                        if (!(r <= x && r <= (BOX - x))) continue;
                        ld l1p = predL1(x, r);
                        ld l2p = predL2(y, r);
                        ld l3p = predL3(x, y, r);
                        if (fabsl(l1p - L1) <= TOL && fabsl(l2p - L2) <= TOL && fabsl(l3p - L3) <= TOL3) {
                            answers.emplace_back(x, y, r);
                            any = true;
                        }
                    }
                }
                if (any) {
                    // continue collecting
                }
            } else {
                // L1 == 0: generate x candidates from diagonal using known y (symmetrical)
                auto xcands = genOtherCoordFromDiag(r, y, L3);
                for (int x : xcands) {
                    if (x < 0 || x > BOX) continue;
                    if (!(r <= x && r <= (BOX - x))) continue;
                    ld l1p = predL1(x, r);
                    if (l1p > 1e-3L) continue;
                    ld l2p = predL2(y, r);
                    ld l3p = predL3(x, y, r);
                    if (fabsl(l2p - L2) <= TOL && fabsl(l3p - L3) <= TOL3) {
                        answers.emplace_back(x, y, r);
                    }
                }
            }
        }
    }

    // Deduplicate and select a valid unique solution
    vector<tuple<int,int,int>> uniq;
    set<tuple<int,int,int>> seen;
    for (auto t : answers) {
        int x,y,r;
        tie(x,y,r)=t;
        if (r < 100 || r > 100000) continue;
        if (x < 0 || x > BOX || y < 0 || y > BOX) continue;
        if (!(r <= x && r <= (BOX - x) && r <= y && r <= (BOX - y))) continue;
        if (!seen.count(t)) {
            seen.insert(t);
            uniq.push_back(t);
        }
    }

    int ansx = 0, ansy = 0, ansr = 100;
    if (!uniq.empty()) {
        // choose the one that matches all three lengths best
        long double bestErr = 1e100;
        tuple<int,int,int> best = uniq[0];
        for (auto t : uniq) {
            int x,y,r;
            tie(x,y,r) = t;
            ld e1 = fabsl(predL1(x,r) - L1);
            ld e2 = fabsl(predL2(y,r) - L2);
            ld e3 = fabsl(predL3(x,y,r) - L3);
            ld err = e1 + e2 + e3;
            if (err < bestErr) {
                bestErr = err;
                best = t;
            }
        }
        tie(ansx, ansy, ansr) = best;
    } else {
        // Fallback: try small brute around plausible ranges if everything failed (unlikely)
        // For safety, we attempt limited search on r around max(L1,L2)/2
        int rmin = 100;
        int rguess = (int)ceill(max(L1, L2) / 2.0L - 1e-9L);
        rmin = max(rmin, rguess);
        int rmax = min(100000, rmin + 2000); // limited window
        bool found = false;
        for (int r = rmin; r <= rmax && !found; ++r) {
            // derive x candidates from L1 if possible
            vector<int> xcand;
            if (L1 > 1e-7) {
                ld half = L1 / 2.0L;
                long long S1b = (long long) llround(half*half);
                for (int dlt = -2; dlt <= 2; ++dlt) {
                    long long d1sq = (long long)r*(long long)r - (S1b + dlt);
                    long long d1;
                    if (!isPerfectSquareLL(d1sq, d1)) continue;
                    long long xs[2] = {(long long)LX - d1, (long long)LX + d1};
                    for (int k = 0; k < 2; ++k) {
                        long long xll = xs[k];
                        if (xll < 0 || xll > BOX) continue;
                        int x = (int)xll;
                        if (r <= x && r <= (BOX - x)) xcand.push_back(x);
                    }
                }
            } else {
                // If L1 == 0, try a few x near borders
                for (int x = r; x <= BOX - r; x += max(1, (BOX - 2*r)/50)) xcand.push_back(x);
            }
            for (int x : xcand) {
                vector<int> ycand;
                if (L2 > 1e-7) {
                    ld half2 = L2 / 2.0L;
                    long long S2b = (long long) llround(half2*half2);
                    for (int dlt = -2; dlt <= 2; ++dlt) {
                        long long d2sq = (long long)r*(long long)r - (S2b + dlt);
                        long long d2;
                        if (!isPerfectSquareLL(d2sq, d2)) continue;
                        long long ys[2] = {(long long)LY - d2, (long long)LY + d2};
                        for (int k = 0; k < 2; ++k) {
                            long long yll = ys[k];
                            if (yll < 0 || yll > BOX) continue;
                            int y = (int)yll;
                            if (r <= y && r <= (BOX - y)) ycand.push_back(y);
                        }
                    }
                } else {
                    auto ys = genOtherCoordFromDiag(r, x, L3);
                    for (int y : ys) if (r <= y && r <= (BOX - y)) ycand.push_back(y);
                }
                for (int y : ycand) {
                    ld e1 = fabsl(predL1(x,r) - L1);
                    ld e2 = fabsl(predL2(y,r) - L2);
                    ld e3 = fabsl(predL3(x,y,r) - L3);
                    if (e1 <= TOL + 5e-4 && e2 <= TOL + 5e-4 && e3 <= TOL3 + 5e-3) {
                        ansx = x; ansy = y; ansr = r;
                        found = true; break;
                    }
                }
                if (found) break;
            }
        }
    }

    cout << "answer " << ansx << " " << ansy << " " << ansr << "\n";
    return 0;
}