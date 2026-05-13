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
    //   if U_base == 0: every feasible solution gets 1,000,000 points => ratio = 1.0
    //   else:  score = floor(10^6 * clamp((U_base - U) / U_base, 0, 1))
    //          ratio = clamp((V - V_base) / (W - V_base), 0, 1)
    long long U_base = totalW - V_base;
    long long U      = totalW - V;

    double ratio;
    if (U_base == 0) {
        // Baseline already covers everything; every feasible answer gets full marks.
        ratio = 1.0;
    } else {
        // ratio = (U_base - U) / U_base = (V - V_base) / (W - V_base)
        ratio = (double)(U_base - U) / (double)U_base;
        if (ratio < 0.0) ratio = 0.0;
        if (ratio > 1.0) ratio = 1.0;
    }

    long long scoreInt = (long long)(1000000.0 * ratio);

    quitp(ratio,
          "V=%lld V_base=%lld W=%lld U=%lld U_base=%lld "
          "Ratio: %.9f Score(x1e6): %lld",
          V, V_base, totalW, U, U_base, ratio, scoreInt);

    return 0;
}