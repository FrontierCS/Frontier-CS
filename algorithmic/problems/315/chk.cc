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

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // ---- Read the input file ----
    int n = inf.readInt();
    int K = inf.readInt();
    long long B = inf.readLong();

    vector<long long> P(n), X(n), W(n);
    long long totalW = 0;
    for (int i = 0; i < n; i++) {
        P[i] = inf.readLong();
        X[i] = inf.readLong();
        W[i] = inf.readLong();
        totalW += W[i];
    }

    // ---- Compute baseline: witnesses (0,0),(1,0),...,(K-1,0) ----
    // Statement guarantees B >= K-1, so all baseline witnesses are valid.
    long long V_base = 0;
    {
        vector<bool> covBase(n, false);
        for (int j = 0; j < K; j++) {
            long long Aj = (long long)j;
            long long Bj = 0LL;
            for (int i = 0; i < n; i++) {
                if (!covBase[i]) {
                    long long am  = Aj % P[i];
                    long long bm  = Bj % P[i];
                    long long val = (am * am + bm * bm) % P[i];
                    if (val == X[i]) {
                        covBase[i] = true;
                        V_base += W[i];
                    }
                }
            }
        }
    }

    // ---- Read participant output ----
    int m = ouf.readInt(0, K, "m must be in [0,K]");

    vector<long long> A(m), Bv(m);
    for (int j = 0; j < m; j++) {
        A[j]  = ouf.readLong();
        Bv[j] = ouf.readLong();
        if (A[j] < 0 || A[j] > B)
            quitf(_wa, "Witness %d: A=%lld is outside [0,%lld]", j + 1, A[j], B);
        if (Bv[j] < 0 || Bv[j] > B)
            quitf(_wa, "Witness %d: B=%lld is outside [0,%lld]", j + 1, Bv[j], B);
    }

    // ---- Strict end-of-file check: reject any trailing tokens ----
    // ouf.seekEof() skips whitespace/newlines before checking for EOF,
    // so well-formed solutions with a trailing newline are accepted.
    if (!ouf.seekEof())
        quitf(_wa, "Extra output found after the %d witness(es)", m);

    // ---- Compute participant objective V ----
    long long V = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            long long am  = A[j]  % P[i];
            long long bm  = Bv[j] % P[i];
            long long val = (am * am + bm * bm) % P[i];
            if (val == X[i]) {
                V += W[i];
                break;
            }
        }
    }

    // ---- Compute score ratio ----
    // Per statement:
    // Base ratio: V/W when U_base == 0, otherwise clamp((V-V_base)/U_base).
    // Apply bounded_base_ratio() to this ratio; only the diagnostic integer is truncated.
    long long U_base = totalW - V_base;
    long long U      = totalW - V;

    double ratio;
    if (U_base == 0) {
        // The baseline is optimal, but a participant must still cover queries.
        ratio = (double)V / (double)totalW;
    } else {
        // ratio = (U_base - U) / U_base = (V - V_base) / (W - V_base)
        ratio = (double)(U_base - U) / (double)U_base;
        if (ratio < 0.0) ratio = 0.0;
        if (ratio > 1.0) ratio = 1.0;
    }

    ratio = bounded_base_ratio(ratio);
    ratio = natural_log_score(100.0L * (ratio), V, (U_base==0 ? 0.6L*totalW : V_base+0.6L*U_base), false) / 100.0;
    long long scoreInt = (long long)(1000000.0 * ratio);

    // Both reported channels use the objective-log score above.
    quitp(ratio,
          "V=%lld V_base=%lld W=%lld U=%lld U_base=%lld "
          "Ratio: %.12f Score(x1e6): %lld",
          V, V_base, totalW, U, U_base, ratio, scoreInt);

    return 0;
}
