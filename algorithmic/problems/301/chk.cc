#include <cmath>
#include <algorithm>

// Keep historical scores through 60; above the anchor, compare physical objectives.
static double natural_log_score(long double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0L) return (double)std::max(0.0L, old_points);
    if (!(value > 0.0L) || !(anchor > 0.0L))
        return (double)std::clamp(old_points, 0.0L, 100.0L);
    const long double improvement = minimize
        ? std::log(anchor) - std::log(value)
        : std::log(value) - std::log(anchor);
    return (double)std::clamp(60.0L + improvement, 0.0L, 100.0L);
}

#include <cmath>
#include <algorithm>

// Historical bounded base ratio; only its <=60-point branch is retained.
static double bounded_base_ratio(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"

#include <bits/stdc++.h>
using namespace std;

using u64 = uint64_t;

struct Pt {
    long double x, y;
};

static inline long double cross(const Pt& a, const Pt& b, const Pt& c) {
    // cross((b-a),(c-a))
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

static inline long double distPointSegment(const Pt& p, const Pt& a, const Pt& b) {
    long double abx = b.x - a.x, aby = b.y - a.y;
    long double apx = p.x - a.x, apy = p.y - a.y;
    long double ab2 = abx * abx + aby * aby;
    long double t = 0.0L;
    if (ab2 > 0) t = (apx * abx + apy * aby) / ab2;
    if (t < 0) t = 0;
    if (t > 1) t = 1;
    long double cx = a.x + t * abx;
    long double cy = a.y + t * aby;
    long double dx = p.x - cx;
    long double dy = p.y - cy;
    return sqrtl(dx * dx + dy * dy);
}

struct XorShiftStar {
    u64 x;
    explicit XorShiftStar(u64 seed) : x(seed) {}
    u64 nextU64() {
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        return x * 2685821657736338717ULL;
    }
    long double nextU01() {
        // uniform in [0,1)
        u64 v = nextU64();
        return ldexpl((long double)v, -64);
    }
};

static bool parseIntStrict(const string& s, long long& out) {
    // Accept optional leading +/-, then digits; no spaces.
    if (s.empty()) return false;
    size_t i = 0;
    if (s[0] == '+' || s[0] == '-') i = 1;
    if (i == s.size()) return false;
    for (; i < s.size(); i++) if (!isdigit((unsigned char)s[i])) return false;
    try {
        size_t pos = 0;
        long long v = stoll(s, &pos, 10);
        if (pos != s.size()) return false;
        out = v;
        return true;
    } catch (...) {
        return false;
    }
}

int main(int argc, char** argv) {
    registerTestlibCmd(argc, argv);

    int n = inf.readInt();
    int m = inf.readInt();
    int K = inf.readInt();
    int S = inf.readInt();
    u64 seed = inf.readUnsignedLong();

    vector<Pt> vtx(n);
    for (int i = 0; i < n; i++) {
        long long xi = inf.readLong();
        long long yi = inf.readLong();
        vtx[i].x = (long double)xi;
        vtx[i].y = (long double)yi;
    }

    vector<pair<int,int>> cand(m);
    for (int j = 0; j < m; j++) {
        int a = inf.readInt();
        int b = inf.readInt();
        cand[j] = {a, b};
    }

    // --- Generate deterministic sample points (uniform in convex polygon via fan triangulation) ---
    // Triangles: (0, i, i+1), i=1..n-2 => count = n-2
    vector<long double> pref; pref.reserve(max(0, n - 2));
    long double totalA = 0.0L;
    for (int i = 1; i <= n - 2; i++) {
        long double area2 = cross(vtx[0], vtx[i], vtx[i+1]); // positive for CCW convex
        long double Ai = area2 / 2.0L;
        totalA += Ai;
        pref.push_back(totalA);
    }

    XorShiftStar rng(seed);
    vector<Pt> samples;
    samples.reserve(S);

    for (int t = 0; t < S; t++) {
        long double r = rng.nextU01() * totalA;
        auto it = upper_bound(pref.begin(), pref.end(), r);
        int idx = (int)(it - pref.begin());   // 0..n-3
        int i = idx + 1;                      // triangle is (0,i,i+1)
        const Pt& a = vtx[0];
        const Pt& b = vtx[i];
        const Pt& c = vtx[i+1];

        long double u = rng.nextU01();
        long double vv = rng.nextU01();
        long double s = sqrtl(u);
        long double alpha = 1.0L - s;
        long double beta  = s * (1.0L - vv);
        long double gamma = s * vv;

        Pt p;
        p.x = alpha * a.x + beta * b.x + gamma * c.x;
        p.y = alpha * a.y + beta * b.y + gamma * c.y;
        samples.push_back(p);
    }

    auto computeOBJ = [&](const vector<int>& ids) -> long double {
        // Prebuild segment endpoints
        vector<pair<Pt,Pt>> segs;
        segs.reserve(ids.size());
        for (int id : ids) {
            auto [u, w] = cand[id];
            segs.push_back({vtx[u], vtx[w]});
        }
        long double sum = 0.0L;
        for (const Pt& p : samples) {
            long double best = numeric_limits<long double>::infinity();
            for (auto& seg : segs) {
                long double d = distPointSegment(p, seg.first, seg.second);
                if (d < best) best = d;
            }
            sum += best;
        }
        return sum / (long double)S;
    };

    // --- Read participant output; treat any format/feasibility issue as infeasible (score 0) ---
    bool feasible = true;
    vector<int> you;
    you.reserve(K);

    for (int i = 0; i < K; i++) {
        if (ouf.seekEof()) { feasible = false; break; }
        string tok = ouf.readToken();
        long long val;
        if (!parseIntStrict(tok, val)) { feasible = false; break; }
        if (val < 0 || val >= m) feasible = false;
        you.push_back((int)val);
    }
    if (feasible && !ouf.seekEof()) feasible = false; // must be exactly K tokens

    if (feasible) {
        vector<int> tmp = you;
        sort(tmp.begin(), tmp.end());
        for (int i = 1; i < (int)tmp.size(); i++) {
            if (tmp[i] == tmp[i-1]) { feasible = false; break; }
        }
    }

    // Baseline: IDs 0..K-1
    vector<int> base;
    base.reserve(K);
    for (int i = 0; i < K; i++) base.push_back(i);

    long double B = computeOBJ(base);

    if (!feasible) {
        // Infeasible output => worst objective; return 0 score ratio.
        quitp(0.0, "Infeasible output. Baseline OBJ=%.12Lf", B);
    }

    long double Y = computeOBJ(you);

    // Scoring: simple baseline-relative improvement
    // ratio = clamp((B - Y)/B, 0..1)
    long double denom = max(B, 1e-30L);
    long double ratioLD = (B - Y) / denom;
    if (ratioLD < 0) ratioLD = 0;
    if (ratioLD > 1) ratioLD = 1;

    double ratio = (double)ratioLD;
    ratio=bounded_base_ratio(ratio);
    ratio = natural_log_score(100.0L * (ratio), Y, B-0.6L*denom, true) / 100.0;
    quitp(ratio, "Ratio: %.12f  BaselineOBJ=%.12Lf  YourOBJ=%.12Lf", ratio, B, Y);
}
