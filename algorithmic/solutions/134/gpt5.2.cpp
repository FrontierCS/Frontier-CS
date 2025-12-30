#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

static inline i128 i128_max(i128 a, i128 b){ return a > b ? a : b; }
static inline i128 i128_min(i128 a, i128 b){ return a < b ? a : b; }

struct Segment {
    int64 l, r;   // inclusive, l<=r
    int64 f;      // max b allowed (can be 0..n)
    int64 h;      // number of b values for each a: max(0, f-LB+1)
};

struct BDist {
    // Represents g(k) = count of points with b <= LB + k - 1 (k >= 0)
    // for current segments, LB fixed.
    vector<int64> H;       // unique heights ascending
    vector<i128> prefW;    // prefix sum of weights (len)
    vector<i128> prefWH;   // prefix sum of weight*height
    i128 totalW = 0;
    i128 totalPairs = 0;

    i128 g(int64 k) const {
        if (k <= 0) return 0;
        // sum w*min(h,k)
        size_t idx = upper_bound(H.begin(), H.end(), k) - H.begin(); // h<=k
        i128 smallWH = prefWH[idx];
        i128 smallW = prefW[idx];
        i128 largeW = totalW - smallW;
        return smallWH + largeW * (i128)k;
    }
};

static inline int64 clampLL(int64 x, int64 lo, int64 hi) {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

struct Solver {
    int64 n;
    int64 LA = 1, LB = 1;

    // Breakpoints for prefix minimum of y. Keys increasing, values strictly decreasing.
    map<int64,int64> bp;

    int queries = 0;

    Solver(int64 n_) : n(n_) {}

    void addConstraint(int64 x, int64 y) {
        // Adds constraint: forbid (a>=x and b>=y).
        // Maintains bp as prefix-min breakpoints (strictly decreasing y).
        auto it = bp.lower_bound(x);
        int64 prevVal = (it == bp.begin() ? n + 1 : prev(it)->second);
        int64 curValAtX = prevVal;
        if (it != bp.end() && it->first == x) curValAtX = it->second;
        int64 newValAtX = min(curValAtX, y);
        if (newValAtX == curValAtX) return;

        if (it != bp.end() && it->first == x) {
            it->second = newValAtX;
        } else {
            it = bp.insert(it, {x, newValAtX});
        }

        // Remove following breakpoints that are now redundant (value >= newValAtX)
        auto jt = next(it);
        while (jt != bp.end() && jt->second >= newValAtX) {
            jt = bp.erase(jt);
        }
    }

    vector<Segment> buildSegments() const {
        vector<Segment> segs;
        int64 cur = n + 1;
        int64 prevX = 1;

        auto pushSeg = [&](int64 L, int64 R, int64 curPref) {
            if (R < LA || L > n) return;
            int64 l = max<int64>(L, LA);
            int64 r = min<int64>(R, n);
            if (l > r) return;
            int64 f = min<int64>(n, curPref - 1);
            int64 h = 0;
            if (f >= LB) h = f - LB + 1;
            segs.push_back({l, r, f, h});
        };

        for (auto &kv : bp) {
            int64 x = kv.first;
            int64 y = kv.second;
            if (x > n) break;
            if (prevX <= x - 1) pushSeg(prevX, x - 1, cur);
            cur = y;
            prevX = x;
        }
        if (prevX <= n) pushSeg(prevX, n, cur);

        // Ensure sorted
        // (pushSeg already keeps order)
        return segs;
    }

    static i128 totalSize(const vector<Segment>& segs) {
        i128 S = 0;
        for (const auto &s : segs) {
            if (s.h <= 0) continue;
            i128 len = (i128)(s.r - s.l + 1);
            S += len * (i128)s.h;
        }
        return S;
    }

    static int64 quantileA(const vector<Segment>& segs, i128 t) {
        // smallest x with count(a<=x) >= t
        i128 cum = 0;
        for (const auto &s : segs) {
            if (s.h <= 0) continue;
            i128 len = (i128)(s.r - s.l + 1);
            i128 contrib = len * (i128)s.h;
            if (cum + contrib >= t) {
                i128 need = t - cum; // 1..contrib
                i128 step = (need + (i128)s.h - 1) / (i128)s.h; // number of a's needed in this segment
                int64 a = s.l + (int64)(step - 1);
                return a;
            }
            cum += contrib;
        }
        // Should not reach if t<=total
        return segs.empty() ? 1 : segs.back().r;
    }

    static BDist buildBDist(const vector<Segment>& segs) {
        vector<pair<int64, int64>> hv; // (height, weight=len)
        hv.reserve(segs.size());
        i128 totalPairs = 0;
        i128 totalW = 0;
        for (const auto &s : segs) {
            if (s.h <= 0) continue;
            int64 len = s.r - s.l + 1;
            hv.push_back({s.h, len});
            totalPairs += (i128)len * (i128)s.h;
            totalW += (i128)len;
        }
        sort(hv.begin(), hv.end());
        // compress equal heights
        vector<pair<int64, i128>> comp;
        for (auto &p : hv) {
            if (comp.empty() || comp.back().first != p.first) comp.push_back({p.first, (i128)p.second});
            else comp.back().second += (i128)p.second;
        }

        BDist dist;
        dist.totalPairs = totalPairs;
        dist.totalW = totalW;
        dist.H.reserve(comp.size());
        dist.prefW.assign(comp.size() + 1, 0);
        dist.prefWH.assign(comp.size() + 1, 0);
        for (size_t i = 0; i < comp.size(); i++) {
            int64 h = comp[i].first;
            i128 w = comp[i].second;
            dist.H.push_back(h);
            dist.prefW[i + 1] = dist.prefW[i] + w;
            dist.prefWH[i + 1] = dist.prefWH[i] + w * (i128)h;
        }
        return dist;
    }

    static int64 quantileB(int64 LB, const BDist& dist, i128 t) {
        // Find smallest y with count(b<=y) >= t
        if (dist.H.empty()) return LB; // should not if t>0
        int64 maxH = dist.H.back();
        int64 lo = 1, hi = maxH;
        while (lo < hi) {
            int64 mid = lo + (hi - lo) / 2;
            if (dist.g(mid) >= t) hi = mid;
            else lo = mid + 1;
        }
        int64 k = lo;
        return LB + k - 1;
    }

    static vector<pair<int64,int64>> enumerateCandidates(const vector<Segment>& segs, int64 LB, int limit) {
        vector<pair<int64,int64>> cand;
        cand.reserve(limit);
        for (const auto &s : segs) {
            if (s.h <= 0) continue;
            for (int64 a = s.l; a <= s.r && (int)cand.size() < limit; a++) {
                for (int64 off = 0; off < s.h && (int)cand.size() < limit; off++) {
                    cand.push_back({a, LB + off});
                }
            }
            if ((int)cand.size() >= limit) break;
        }
        return cand;
    }

    int ask(int64 x, int64 y) {
        x = clampLL(x, 1, n);
        y = clampLL(y, 1, n);
        cout << x << " " << y << "\n";
        cout.flush();
        queries++;
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        if (ans == 0) exit(0);
        if (ans == 1) LA = max(LA, x + 1);
        else if (ans == 2) LB = max(LB, y + 1);
        else if (ans == 3) addConstraint(x, y);
        return ans;
    }

    void run() {
        while (true) {
            if (queries > 10000) return;

            auto segs = buildSegments();
            i128 S = totalSize(segs);

            if (S <= (i128)50) {
                // small brute-force
                int cnt = (int)S;
                auto cand = enumerateCandidates(segs, LB, max(1, cnt));
                if (cand.empty()) {
                    // Should not happen
                    ask(LA, LB);
                    continue;
                }
                for (auto &p : cand) {
                    ask(p.first, p.second);
                }
                continue;
            }

            i128 t = (S + 2) / 3; // ceil(S/3)
            auto dist = buildBDist(segs);

            int64 x = quantileA(segs, t);
            int64 y = quantileB(LB, dist, t);

            ask(x, y);
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    Solver solver(n);
    solver.run();
    return 0;
}