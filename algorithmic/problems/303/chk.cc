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


#include <algorithm>
// Historical bounded base ratio; only its <=60-point branch is retained.
static double bounded_base_ratio(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

static inline long long manhattan(long long x1, long long y1, long long x2, long long y2) {
    return llabs(x1 - x2) + llabs(y1 - y2);
}

int main(int argc, char** argv) {
    registerTestlibCmd(argc, argv);

    int N = inf.readInt();
    int L = inf.readInt();
    int a = inf.readInt();
    int b = inf.readInt();
    long long c = inf.readLong();

    vector<long long> x(N + 1), y(N + 1), w(N + 1);
    for (int i = 1; i <= N; i++) {
        x[i] = inf.readLong();
        y[i] = inf.readLong();
        w[i] = inf.readLong();
    }

    long long P0 = w[a] + w[b];
    long long total_value = accumulate(w.begin(), w.end(), 0LL);

    // Allow completely empty output => interpret as 0 moves.
    int S = 0;
    if (!ouf.eof()) {
        S = ouf.readInt();
    } else {
        S = 0;
    }

    if (S < 0) quitf(_wa, "S is negative: %d", S);
    if (S > L) quitf(_wa, "Too many moves: S=%d > L=%d", S, L);

    vector<char> touched(N + 1, 0);
    long long collected = 0;
    auto touch = [&](int i) {
        if (!touched[i]) {
            touched[i] = 1;
            collected += w[i];
        }
    };

    touch(a);
    touch(b);

    int p = a, q = b; // previous pair (unordered conceptually)

    for (int t = 1; t <= S; t++) {
        int u = ouf.readInt();
        int v = ouf.readInt();

        if (u < 1 || u > N || v < 1 || v > N) {
            quitf(_wa, "Move %d has out-of-range pinhole index: (%d,%d)", t, u, v);
        }
        if (u == v) {
            quitf(_wa, "Move %d touches same pinhole twice: (%d,%d)", t, u, v);
        }

        // Must share exactly one endpoint with previous pair {p,q}
        bool uInPrev = (u == p || u == q);
        bool vInPrev = (v == p || v == q);

        if (uInPrev && vInPrev) {
            quitf(_wa, "Move %d shares two endpoints with previous pair (no change): prev={%d,%d}, now={%d,%d}", t, p, q, u, v);
        }
        if (!uInPrev && !vInPrev) {
            quitf(_wa, "Move %d shares zero endpoints with previous pair: prev={%d,%d}, now={%d,%d}", t, p, q, u, v);
        }

        int shared = uInPrev ? u : v;
        int newOther = uInPrev ? v : u;

        int oldOther;
        if (shared == p) oldOther = q;
        else if (shared == q) oldOther = p;
        else {
            // Should be impossible due to uInPrev/vInPrev logic
            quitf(_wa, "Internal error determining shared endpoint at move %d", t);
        }

        long long d1 = manhattan(x[shared], y[shared], x[oldOther], y[oldOther]);
        long long d2 = manhattan(x[shared], y[shared], x[newOther], y[newOther]);
        if (d1 != d2) {
            quitf(_wa,
                  "Move %d violates equal-distance rule: shared=%d oldOther=%d newOther=%d d_old=%lld d_new=%lld",
                  t, shared, oldOther, newOther, d1, d2);
        }

        // Accept move; update state and touched set
        touch(u);
        touch(v);
        p = u;
        q = v;
    }

    // No extra tokens allowed
    ouf.seekEof();

    long long profit = collected - c * 1LL * S;

    double ratio = 0.0;
    if (profit > 0) {
        // With a zero baseline, use the physical profit upper bound.
        ratio = P0 == 0
            ? (total_value > 0 ? double(profit) / double(total_value) : 0.0)
            : double(profit - P0) / double(profit);
        if (ratio < 0.0) ratio = 0.0;
        if (ratio > 1.0) ratio = 1.0;
    }

    ratio = bounded_base_ratio(ratio);
    ratio = natural_log_score(100.0L * (ratio), profit, (P0>0 ? 2.5L*P0 : 0.6L*total_value), false) / 100.0;
    quitp(ratio,
          "Ratio: %.12f Profit=%lld Baseline=%lld Moves=%d Collected=%lld CostPerMove=%lld",
          ratio, profit, P0, S, collected, c);
}
