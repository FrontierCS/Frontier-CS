#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;
using u128 = __uint128_t;

struct Seg {
    ull l, r;   // inclusive range of a
    ull ub;     // upper bound for b on this range
};

static inline u128 segMeasure(const Seg& s, ull lb) {
    if (s.ub < lb) return 0;
    ull len = s.r - s.l + 1;
    ull width = s.ub - lb + 1;
    return (u128)len * (u128)width;
}

struct State {
    ull n;
    ull la = 1, lb = 1;
    vector<Seg> segs; // non-increasing ub, contiguous from la to amax, all ub >= lb

    explicit State(ull n_) : n(n_) {
        segs.push_back({1, n, n});
    }

    void mergeAdjacent() {
        if (segs.empty()) return;
        vector<Seg> merged;
        merged.reserve(segs.size());
        merged.push_back(segs[0]);
        for (size_t i = 1; i < segs.size(); i++) {
            auto &back = merged.back();
            if (back.r + 1 == segs[i].l && back.ub == segs[i].ub) {
                back.r = segs[i].r;
            } else {
                merged.push_back(segs[i]);
            }
        }
        segs.swap(merged);
    }

    void normalize() {
        if (segs.empty()) return;

        // trim left of la
        while (!segs.empty() && segs.front().r < la) segs.erase(segs.begin());
        if (segs.empty()) return;
        if (segs.front().l < la) segs.front().l = la;

        // trim tail where ub < lb (since ub non-increasing, can cut all later)
        vector<Seg> kept;
        kept.reserve(segs.size());
        for (const auto& s : segs) {
            if (s.ub < lb) break;
            if (s.l <= s.r) kept.push_back(s);
        }
        segs.swap(kept);

        mergeAdjacent();
    }

    ull amax() const {
        return segs.empty() ? 0 : segs.back().r;
    }
    ull bmax() const {
        return segs.empty() ? 0 : segs.front().ub;
    }

    u128 totalMeasure() const {
        u128 tot = 0;
        for (const auto& s : segs) tot += segMeasure(s, lb);
        return tot;
    }

    ull ubAt(ull a) const {
        for (const auto& s : segs) {
            if (s.l <= a && a <= s.r) return s.ub;
        }
        // should not happen for valid a
        return 0;
    }

    // Update after response 1: x < a => a >= x+1
    void updateA_lower(ull x) {
        ull nl = x + 1;
        if (nl > la) la = nl;
        if (la > n) la = n + 1;
        normalize();
    }

    // Update after response 2: y < b => b >= y+1
    void updateB_lower(ull y) {
        ull nl = y + 1;
        if (nl > lb) lb = nl;
        if (lb > n) lb = n + 1;
        normalize();
    }

    // Update after response 3: x > a OR y > b => a <= x-1 OR b <= y-1
    // Equivalent: for all a >= x, require b <= y-1
    void applyClause(ull x, ull y) {
        if (segs.empty()) return;
        ull newUb = (y == 0 ? 0 : y - 1);
        ull am = amax();
        if (x <= la) x = la;
        if (x > am) return;

        vector<Seg> out;
        out.reserve(segs.size() + 2);

        bool clipping = true;
        for (const auto& s0 : segs) {
            Seg s = s0;
            if (s.r < x) {
                out.push_back(s);
                continue;
            }
            if (s.l < x) {
                out.push_back({s.l, x - 1, s.ub});
                s.l = x;
            }
            // now s.l >= x
            if (clipping && s.ub > newUb) {
                out.push_back({s.l, s.r, newUb});
                // clipping continues
            } else {
                out.push_back(s);
                if (clipping && s.ub <= newUb) clipping = false;
            }
        }

        segs.swap(out);
        normalize();
    }

    u128 measureAfter1(ull x) const {
        if (segs.empty()) return 0;
        ull newLa = max(la, x + 1);
        ull am = amax();
        if (newLa > am) return 0;
        u128 res = 0;
        for (const auto& s : segs) {
            if (s.r < newLa) continue;
            ull l = max(s.l, newLa);
            ull len = s.r - l + 1;
            if (s.ub < lb) break;
            ull width = s.ub - lb + 1;
            res += (u128)len * (u128)width;
        }
        return res;
    }

    u128 measureAfter2(ull y) const {
        if (segs.empty()) return 0;
        ull newLb = max(lb, y + 1);
        if (newLb > n) return 0;
        u128 res = 0;
        for (const auto& s : segs) {
            if (s.ub < newLb) break; // ub non-increasing
            ull len = s.r - s.l + 1;
            ull width = s.ub - newLb + 1;
            res += (u128)len * (u128)width;
        }
        return res;
    }

    u128 measureAfter3(ull x, ull y) const {
        if (segs.empty()) return 0;
        ull am = amax();
        if (x > am) return totalMeasure();
        ull newUb = (y == 0 ? 0 : y - 1);

        u128 res = 0;
        bool clipping = true;
        for (const auto& s : segs) {
            if (s.ub < lb) break;
            ull width0 = s.ub - lb + 1;
            if (s.r < x) {
                ull len = s.r - s.l + 1;
                res += (u128)len * (u128)width0;
                continue;
            }

            if (s.l < x) {
                ull lenLeft = x - s.l;
                res += (u128)lenLeft * (u128)width0;
                // right part
                ull lenRight = s.r - x + 1;
                ull ub = s.ub;
                ull ub2 = ub;
                if (clipping && ub > newUb) ub2 = newUb;
                else if (clipping && ub <= newUb) clipping = false;
                if (ub2 >= lb) {
                    ull width = ub2 - lb + 1;
                    res += (u128)lenRight * (u128)width;
                }
            } else {
                ull len = s.r - s.l + 1;
                ull ub = s.ub;
                ull ub2 = ub;
                if (clipping && ub > newUb) ub2 = newUb;
                else if (clipping && ub <= newUb) clipping = false;
                if (ub2 >= lb) {
                    ull width = ub2 - lb + 1;
                    res += (u128)len * (u128)width;
                }
            }
        }
        return res;
    }

    ull quantileA(u128 target) const {
        // target in [1..total]
        u128 pref = 0;
        for (const auto& s : segs) {
            if (s.ub < lb) break;
            ull width = s.ub - lb + 1;
            ull len = s.r - s.l + 1;
            u128 segTot = (u128)len * (u128)width;
            if (pref + segTot >= target) {
                u128 off = target - pref - 1;
                ull da = (ull)(off / (u128)width);
                ull a = s.l + da;
                if (a > s.r) a = s.r;
                return a;
            }
            pref += segTot;
        }
        return amax();
    }

    u128 countB_le(ull t) const {
        if (segs.empty() || t < lb) return 0;
        u128 res = 0;
        for (const auto& s : segs) {
            ull hi = min(s.ub, t);
            if (hi < lb) {
                // since ub non-increasing, if s.ub < lb then all later also < lb
                if (s.ub < lb) break;
                continue;
            }
            ull len = s.r - s.l + 1;
            ull width = hi - lb + 1;
            res += (u128)len * (u128)width;
        }
        return res;
    }

    ull quantileB(u128 target) const {
        ull lo = lb, hi = bmax();
        if (lo > hi) return lo;
        while (lo < hi) {
            ull mid = lo + ((hi - lo) >> 1);
            if (countB_le(mid) >= target) hi = mid;
            else lo = mid + 1;
        }
        return lo;
    }

    static inline bool leq_u128_u64(u128 v, ull x) {
        return v <= (u128)x;
    }
};

static bool readInt(int &x) {
    if (!(cin >> x)) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ull n;
    if (!(cin >> n)) return 0;

    State st(n);

    const ull QUERY_LIMIT = 10000;
    ull queries = 0;

    while (queries < QUERY_LIMIT) {
        u128 tot = st.totalMeasure();
        if (tot == 0) return 0;

        if (tot == 1) {
            ull a = st.la;
            ull b = st.lb;
            cout << a << " " << b << "\n";
            cout.flush();
            int r;
            if (!readInt(r)) return 0;
            if (r == 0) return 0;
            // Should never happen with correct state; fall back to updates.
            if (r == 1) st.updateA_lower(a);
            else if (r == 2) st.updateB_lower(b);
            else if (r == 3) st.applyClause(a, b);
            queries++;
            continue;
        }

        if (st.leq_u128_u64(tot, 64)) {
            // brute force all candidates
            vector<pair<ull, ull>> cand;
            cand.reserve(64);
            for (const auto& seg : st.segs) {
                for (ull a = seg.l; a <= seg.r; a++) {
                    for (ull b = st.lb; b <= seg.ub; b++) {
                        cand.push_back({a, b});
                        if (cand.size() >= 64) break;
                    }
                    if (cand.size() >= 64) break;
                    if (a == seg.r) break; // avoid overflow
                }
                if (cand.size() >= 64) break;
            }
            for (auto [a, b] : cand) {
                cout << a << " " << b << "\n";
                cout.flush();
                int r;
                if (!readInt(r)) return 0;
                queries++;
                if (r == 0) return 0;
                // ignore updates; secret fixed, we will hit it in this list
                if (queries >= QUERY_LIMIT) return 0;
            }
            // If not found (shouldn't), continue with normal logic
            continue;
        }

        ull am = st.amax();
        ull bm = st.bmax();
        if (am < st.la || bm < st.lb) return 0;

        auto ceilMulDiv = [&](u128 v, ull num, ull den) -> u128 {
            return (v * (u128)num + (u128)(den - 1)) / (u128)den;
        };

        vector<ull> xCands;
        xCands.push_back(st.la);
        xCands.push_back(am);

        u128 t1 = ceilMulDiv(tot, 1, 3);
        u128 t2 = ceilMulDiv(tot, 1, 2);
        u128 t3 = ceilMulDiv(tot, 2, 3);
        t1 = max<u128>(1, min<u128>(tot, t1));
        t2 = max<u128>(1, min<u128>(tot, t2));
        t3 = max<u128>(1, min<u128>(tot, t3));

        xCands.push_back(st.quantileA(t1));
        xCands.push_back(st.quantileA(t2));
        xCands.push_back(st.quantileA(t3));

        sort(xCands.begin(), xCands.end());
        xCands.erase(unique(xCands.begin(), xCands.end()), xCands.end());
        for (auto &x : xCands) {
            if (x < st.la) x = st.la;
            if (x > am) x = am;
        }
        sort(xCands.begin(), xCands.end());
        xCands.erase(unique(xCands.begin(), xCands.end()), xCands.end());

        vector<ull> yBase;
        yBase.push_back(st.lb);
        yBase.push_back(bm);

        u128 b1 = ceilMulDiv(tot, 1, 3);
        u128 b2 = ceilMulDiv(tot, 1, 2);
        u128 b3 = ceilMulDiv(tot, 2, 3);
        b1 = max<u128>(1, min<u128>(tot, b1));
        b2 = max<u128>(1, min<u128>(tot, b2));
        b3 = max<u128>(1, min<u128>(tot, b3));

        yBase.push_back(st.quantileB(b1));
        yBase.push_back(st.quantileB(b2));
        yBase.push_back(st.quantileB(b3));

        sort(yBase.begin(), yBase.end());
        yBase.erase(unique(yBase.begin(), yBase.end()), yBase.end());
        for (auto &y : yBase) {
            if (y < st.lb) y = st.lb;
            if (y > bm) y = bm;
        }
        sort(yBase.begin(), yBase.end());
        yBase.erase(unique(yBase.begin(), yBase.end()), yBase.end());

        ull bestX = st.la, bestY = st.lb;
        u128 bestWorst = tot;

        for (ull x : xCands) {
            ull ubx = st.ubAt(x);
            vector<ull> yCands = yBase;
            yCands.push_back(ubx);
            for (ull y : yBase) yCands.push_back(min(y, ubx));
            sort(yCands.begin(), yCands.end());
            yCands.erase(unique(yCands.begin(), yCands.end()), yCands.end());

            for (ull y : yCands) {
                if (y < 1) y = 1;
                if (y > n) y = n;
                // keep informative
                if (y < st.lb) y = st.lb;
                if (y > bm) y = bm;

                u128 s1 = st.measureAfter1(x);
                u128 s2 = st.measureAfter2(y);
                u128 s3 = st.measureAfter3(x, y);
                u128 worst = max(s1, max(s2, s3));

                if (worst < bestWorst) {
                    bestWorst = worst;
                    bestX = x;
                    bestY = y;
                }
            }
        }

        if (bestWorst >= tot) {
            bestX = st.la;
            bestY = st.lb + ((bm - st.lb) >> 1);
            if (bestY < st.lb) bestY = st.lb;
            if (bestY > bm) bestY = bm;
        }

        cout << bestX << " " << bestY << "\n";
        cout.flush();

        int r;
        if (!readInt(r)) return 0;
        queries++;

        if (r == 0) return 0;
        if (r == 1) st.updateA_lower(bestX);
        else if (r == 2) st.updateB_lower(bestY);
        else if (r == 3) st.applyClause(bestX, bestY);
        else return 0;
    }

    return 0;
}