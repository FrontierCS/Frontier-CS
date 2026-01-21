#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

static inline i128 imax(i128 a, i128 b) { return a > b ? a : b; }

struct Segment {
    int64 L, R;
    int64 U; // max b for any a in [L,R]
};

struct State {
    int64 n;
    int64 la = 1, lb = 1;
    vector<pair<int64,int64>> c3; // constraints from answer 3: (x,y) => a < x OR b < y
    vector<Segment> segs;
    vector<int64> starts;
    vector<int64> pairsPerA; // for each segment: U - lb + 1
    vector<i128> suffixPairs; // size segs.size()+1
    int64 ra = 0;   // max feasible a
    int64 maxB = 0; // F(la)
    i128 total = 0;
};

static inline i128 mulDiv(i128 v, int64 mul, int64 div) {
    // floor(v * mul / div) without overflow for small div
    i128 q = v / div;
    i128 r = v % div;
    return q * mul + (r * mul) / div;
}

struct Interactor {
    int queries = 0;
    int64 n;
    Interactor(int64 n_) : n(n_) {}

    int ask(int64 x, int64 y) {
        ++queries;
        cout << x << " " << y << "\n" << flush;
        int r;
        if (!(cin >> r)) exit(0);
        if (r == 0) exit(0);
        return r;
    }
};

static void rebuild(State &st) {
    vector<pair<int64,int64>> v;
    v.reserve(st.c3.size());
    for (auto [x, y] : st.c3) {
        int64 u = y - 1; // b <= u if a >= x
        v.push_back({x, u});
    }
    sort(v.begin(), v.end());
    // compress by x with minimal u
    vector<pair<int64,int64>> w;
    w.reserve(v.size());
    for (auto &p : v) {
        if (w.empty() || w.back().first != p.first) w.push_back(p);
        else w.back().second = min(w.back().second, p.second);
    }

    vector<Segment> all;
    all.reserve(w.size() + 1);
    int64 cur = st.n;
    int64 prev = 1;
    for (auto [x, u] : w) {
        if (prev <= x - 1) all.push_back({prev, x - 1, cur});
        cur = min(cur, u);
        prev = x;
    }
    if (prev <= st.n) all.push_back({prev, st.n, cur});

    st.segs.clear();
    st.starts.clear();
    st.pairsPerA.clear();
    st.suffixPairs.clear();
    st.total = 0;
    st.ra = st.la - 1;
    st.maxB = 0;

    for (auto &sg : all) {
        if (sg.R < st.la) continue;
        int64 L = max(sg.L, st.la);
        int64 R = sg.R;
        if (L > R) continue;
        int64 U = sg.U;
        if (U < st.lb) break; // since U non-increasing with a
        st.segs.push_back({L, R, U});
    }

    if (st.segs.empty()) {
        st.ra = st.la - 1;
        st.maxB = st.lb - 1;
        st.total = 0;
        return;
    }

    st.starts.reserve(st.segs.size());
    st.pairsPerA.reserve(st.segs.size());
    for (auto &sg : st.segs) {
        st.starts.push_back(sg.L);
        st.pairsPerA.push_back((int64)((i128)sg.U - st.lb + 1));
    }

    st.suffixPairs.assign(st.segs.size() + 1, 0);
    for (int i = (int)st.segs.size() - 1; i >= 0; --i) {
        auto &sg = st.segs[i];
        i128 len = (i128)sg.R - sg.L + 1;
        i128 cnt = (i128)st.pairsPerA[i];
        st.suffixPairs[i] = st.suffixPairs[i + 1] + len * cnt;
    }
    st.total = st.suffixPairs[0];
    st.ra = st.segs.back().R;
    st.maxB = st.segs.front().U;
}

static int segIndexOf(const State &st, int64 a) {
    // assumes st.segs non-empty and a in [la, ra]
    int idx = int(upper_bound(st.starts.begin(), st.starts.end(), a) - st.starts.begin()) - 1;
    if (idx < 0) idx = 0;
    return idx;
}

static int64 upperAt(const State &st, int64 a) {
    int idx = segIndexOf(st, a);
    return st.segs[idx].U;
}

static i128 countS1(const State &st, int64 x) {
    // pairs with a > x
    if (st.total == 0) return 0;
    if (x >= st.ra) return 0;
    if (x < st.la) return st.total;
    int idx = segIndexOf(st, x);
    const Segment &sg = st.segs[idx];
    i128 res = st.suffixPairs[idx + 1];
    if (x < sg.R) {
        i128 len = (i128)sg.R - x;
        i128 cnt = (i128)st.pairsPerA[idx];
        res += len * cnt;
    }
    return res;
}

static i128 countS2(const State &st, int64 y) {
    // pairs with b > y  <=> b >= y+1
    if (st.total == 0) return 0;
    int64 lowb = max(st.lb, y + 1);
    i128 res = 0;
    for (auto &sg : st.segs) {
        if (sg.U < lowb) continue;
        i128 len = (i128)sg.R - sg.L + 1;
        i128 cnt = (i128)sg.U - lowb + 1;
        res += len * cnt;
    }
    return res;
}

static i128 countNE(const State &st, int64 x, int64 y) {
    // pairs with a >= x and b >= y
    if (st.total == 0) return 0;
    if (x > st.ra) return 0;
    int64 lowb = max(st.lb, y);
    i128 res = 0;
    int startIdx = 0;
    if (x > st.la) startIdx = segIndexOf(st, x);
    for (int i = startIdx; i < (int)st.segs.size(); ++i) {
        auto &sg = st.segs[i];
        if (sg.R < x) continue;
        int64 L = max(sg.L, x);
        if (L > sg.R) continue;
        if (sg.U < lowb) continue;
        i128 len = (i128)sg.R - L + 1;
        i128 cnt = (i128)sg.U - lowb + 1;
        res += len * cnt;
    }
    return res;
}

static i128 evalM(const State &st, int64 x, int64 y) {
    i128 s1 = countS1(st, x);
    i128 s2 = countS2(st, y);
    i128 ne = countNE(st, x, y);
    i128 s3 = st.total - ne;
    return imax(s1, imax(s2, s3));
}

static int64 findX(const State &st, i128 target) {
    int64 lo = st.la, hi = st.ra;
    while (lo < hi) {
        int64 mid = lo + ((hi - lo) >> 1);
        if (countS1(st, mid) <= target) hi = mid;
        else lo = mid + 1;
    }
    return lo;
}

static int64 findY(const State &st, int64 ymax, i128 target) {
    int64 lo = st.lb, hi = ymax;
    while (lo < hi) {
        int64 mid = lo + ((hi - lo) >> 1);
        if (countS2(st, mid) <= target) hi = mid;
        else lo = mid + 1;
    }
    return lo;
}

static int64 balanceY(const State &st, int64 x, int64 ymax) {
    int64 lo = st.lb, hi = ymax;
    while (lo < hi) {
        int64 mid = lo + ((hi - lo) >> 1);
        i128 A = countS2(st, mid);
        i128 B = st.total - countNE(st, x, mid);
        if (A > B) lo = mid + 1;
        else hi = mid;
    }
    return lo;
}

static pair<int64,int64> chooseQuery(const State &st) {
    // assumes st.total > 1 and segs non-empty
    i128 S = st.total;

    vector<int64> xs;
    auto addx = [&](int64 v) {
        v = max(v, st.la);
        v = min(v, st.ra);
        xs.push_back(v);
    };

    addx(st.la);
    addx(st.ra);
    addx(st.la + (st.ra - st.la) / 2);
    addx(findX(st, S / 2));
    addx(findX(st, mulDiv(S, 618, 1000)));
    addx(findX(st, mulDiv(S, 2, 3)));

    vector<int64> tmp = xs;
    for (int64 v : tmp) {
        addx(v - 1);
        addx(v + 1);
    }
    sort(xs.begin(), xs.end());
    xs.erase(unique(xs.begin(), xs.end()), xs.end());

    i128 bestM = -1;
    int64 bestx = st.la, besty = st.lb;

    for (int64 x : xs) {
        int64 ymax = min<int64>(st.maxB, upperAt(st, x));
        ymax = max(ymax, st.lb);

        int64 yBal = balanceY(st, x, ymax);
        int64 yHalf = findY(st, ymax, S / 2);
        int64 yPhi = findY(st, ymax, mulDiv(S, 618, 1000));

        vector<int64> ys;
        auto addy = [&](int64 v) {
            v = max(v, st.lb);
            v = min(v, ymax);
            ys.push_back(v);
        };

        addy(st.lb);
        addy(ymax);
        addy(yBal); addy(yBal - 1); addy(yBal + 1);
        addy(yHalf); addy(yHalf - 1); addy(yHalf + 1);
        addy(yPhi); addy(yPhi - 1); addy(yPhi + 1);

        sort(ys.begin(), ys.end());
        ys.erase(unique(ys.begin(), ys.end()), ys.end());

        for (int64 y : ys) {
            // ensure y is not above F(x), already clamped to ymax<=upperAt(x)
            i128 M = evalM(st, x, y);
            if (bestM < 0 || M < bestM) {
                bestM = M;
                bestx = x;
                besty = y;
            }
        }
    }

    // guarantee within range
    bestx = max<int64>(1, min(bestx, st.n));
    besty = max<int64>(1, min(besty, st.n));
    return {bestx, besty};
}

static void updateState(State &st, int64 x, int64 y, int r) {
    if (r == 1) st.la = max(st.la, x + 1);
    else if (r == 2) st.lb = max(st.lb, y + 1);
    else if (r == 3) st.c3.push_back({x, y});
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    State st;
    cin >> st.n;
    st.la = 1;
    st.lb = 1;

    Interactor io(st.n);

    const i128 BRUTE_T = 3000;

    while (io.queries < 10000) {
        rebuild(st);
        if (st.total <= 0) {
            // Should never happen with correct interaction.
            return 0;
        }

        // If a is fixed, binary search b with unambiguous answers (0/2/3)
        if (st.la == st.ra) {
            int64 a = st.la;
            int64 lo = st.lb;
            int64 hi = upperAt(st, a);
            while (lo <= hi && io.queries < 10000) {
                int64 mid = lo + ((hi - lo) >> 1);
                int r = io.ask(a, mid);
                if (r == 2) {
                    lo = mid + 1;
                    st.lb = max(st.lb, mid + 1);
                } else if (r == 3) {
                    hi = mid - 1;
                    st.c3.push_back({a, mid});
                } else if (r == 1) {
                    // Shouldn't happen if a is correct, but keep consistent
                    st.la = max(st.la, a + 1);
                    break;
                }
                rebuild(st);
                if (st.total == 1) break;
            }
            continue;
        }

        // If b is fixed, binary search a with unambiguous answers (0/1/3)
        if (st.maxB == st.lb) {
            int64 b = st.lb;
            int64 lo = st.la;
            int64 hi = st.ra;
            while (lo <= hi && io.queries < 10000) {
                int64 mid = lo + ((hi - lo) >> 1);
                int r = io.ask(mid, b);
                if (r == 1) {
                    lo = mid + 1;
                    st.la = max(st.la, mid + 1);
                } else if (r == 3) {
                    hi = mid - 1;
                    st.c3.push_back({mid, b});
                } else if (r == 2) {
                    // Shouldn't happen if b is correct, but keep consistent
                    st.lb = max(st.lb, b + 1);
                    break;
                }
                rebuild(st);
                if (st.total == 1) break;
            }
            continue;
        }

        if (st.total <= BRUTE_T) {
            // enumerate all candidates and try them
            vector<pair<int64,int64>> cand;
            cand.reserve((size_t)min<i128>(st.total, BRUTE_T));
            for (auto &sg : st.segs) {
                for (int64 a = sg.L; a <= sg.R; ++a) {
                    for (int64 b = st.lb; b <= sg.U; ++b) {
                        cand.push_back({a, b});
                        if ((i128)cand.size() > BRUTE_T) break;
                    }
                    if ((i128)cand.size() > BRUTE_T) break;
                }
                if ((i128)cand.size() > BRUTE_T) break;
            }

            if (cand.empty()) return 0;

            auto [x, y] = cand[0];
            int r = io.ask(x, y);
            updateState(st, x, y, r);
            continue;
        }

        auto [x, y] = chooseQuery(st);
        int r = io.ask(x, y);
        updateState(st, x, y, r);
    }

    return 0;
}