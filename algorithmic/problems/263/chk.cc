#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

static inline long double clamp01(long double x) {
    if (x < 0) return 0;
    if (x > 1) return 1;
    return x;
}

int main(int argc, char** argv) {
    registerTestlibCmd(argc, argv);

    int n = inf.readInt(3, 4000, "n");
    int m = inf.readInt(1, 2000000, "m");
    int Dlim = inf.readInt(0, min(m, 200000), "D");

    vector<int> U(m + 1), V(m + 1);
    vector<int> W(m + 1);
    vector<int64_t> X(m + 1);

    long double L_base = 0.0L;

    for (int k = 1; k <= m; k++) {
        int u = inf.readInt(1, n, ("u" + to_string(k)).c_str());
        int v = inf.readInt(1, n, ("v" + to_string(k)).c_str());
        if (u == v) quitf(_fail, "Input invalid: u==v at k=%d", k);

        int64_t x = inf.readLong(1LL, 1000000000LL, ("x" + to_string(k)).c_str());
        int w = inf.readInt(1, 1000, ("w" + to_string(k)).c_str());

        U[k] = u; V[k] = v; X[k] = x; W[k] = w;

        // Baseline is a[i]=1, no discards: p=1
        // e = w * |1 - x| / x = w * (x-1)/x since x>=1
        L_base += (long double)w * ((long double)(x - 1) / (long double)x);
    }

    // Read participant output
    vector<int64_t> A(n + 1);
    for (int i = 1; i <= n; i++) {
        A[i] = ouf.readLong(1LL, 1000000000LL, ("a" + to_string(i)).c_str());
    }

    int t = ouf.readInt(0, Dlim, "t");
    vector<unsigned char> discard(m + 1, 0);

    for (int i = 0; i < t; i++) {
        int idx = ouf.readInt(1, m, ("idx" + to_string(i + 1)).c_str());
        if (discard[idx]) {
            quitf(_wa, "Duplicate discarded observation index: %d", idx);
        }
        discard[idx] = 1;
    }

    ouf.seekEof();

    // Compute participant loss
    long double L_sub = 0.0L;
    for (int k = 1; k <= m; k++) {
        if (discard[k]) continue;

        uint64_t p = (uint64_t)A[U[k]] * (uint64_t)A[V[k]]; // up to 1e18
        uint64_t x = (uint64_t)X[k];
        uint64_t diff = (p >= x) ? (p - x) : (x - p);

        long double ek = (long double)W[k] * ((long double)diff / (long double)x);
        L_sub += ek;
    }

    long double unbounded_ratio = 0.0L;
    if (L_base > 0) unbounded_ratio = (L_base - L_sub) / L_base;
    long double ratio = clamp01(unbounded_ratio);

    quitp((double)ratio,
          "Ratio: %.12Lf RatioUnbounded: %.12Lf L_sub: %.12Lf L_base: %.12Lf discarded: %d",
          ratio, unbounded_ratio, L_sub, L_base, t);
}