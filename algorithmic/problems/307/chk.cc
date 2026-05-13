#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // ── Read problem input ──────────────────────────────────────────────────
    int N = inf.readInt();
    int K = inf.readInt();

    long double P = (long double)inf.readDouble();
    long double A = (long double)inf.readDouble();
    long double B = (long double)inf.readDouble();

    vector<long double> sx(N), sy(N), sd(N);
    for (int j = 0; j < N; j++) {
        sx[j] = (long double)inf.readDouble();
        sy[j] = (long double)inf.readDouble();
        sd[j] = (long double)inf.readDouble();
    }

    // ── Read participant output ─────────────────────────────────────────────
    int M = ouf.readInt();
    if (M < 1 || M > K)
        quitf(_wa, "M=%d is not in [1, K=%d]", M, K);

    vector<long double> hx(M), hy(M);
    for (int i = 0; i < M; i++) {
        hx[i] = (long double)ouf.readDouble();
        hy[i] = (long double)ouf.readDouble();
        if (!isfinite((double)hx[i]) || !isfinite((double)hy[i]))
            quitf(_wa, "Hub %d has non-finite coordinate(s)", i + 1);
        if (fabsl(hx[i]) > 1e9L || fabsl(hy[i]) > 1e9L)
            quitf(_wa, "Hub %d coordinate(s) exceed 1e9 in absolute value", i + 1);
    }

    vector<int> asgn(N);
    for (int j = 0; j < N; j++) {
        asgn[j] = ouf.readInt();
        if (asgn[j] < 1 || asgn[j] > M)
            quitf(_wa, "Sensor %d assignment %d not in [1, M=%d]", j + 1, asgn[j], M);
    }

    // ── Reject trailing garbage ─────────────────────────────────────────────
    if (!ouf.seekEof())
        quitf(_wa, "Extra tokens found after the N assignments");

    // ── Compute participant total cost C ────────────────────────────────────
    vector<long double> load(M, 0.0L), r2(M, 0.0L);
    vector<bool> used(M, false);

    for (int j = 0; j < N; j++) {
        int h = asgn[j] - 1;
        used[h] = true;
        load[h] += sd[j];
        long double dx = hx[h] - sx[j];
        long double dy = hy[h] - sy[j];
        long double dist2 = dx * dx + dy * dy;
        if (dist2 > r2[h]) r2[h] = dist2;
    }

    long double C = 0.0L;
    for (int i = 0; i < M; i++) {
        if (used[i])
            C += P + A * r2[i] + B * load[i] * load[i];
    }

    // ── Compute baseline cost C_base ────────────────────────────────────────
    // 1. Sort sensors by (x_j, y_j, original-index j)
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (sx[a] != sx[b]) return sx[a] < sx[b];
        if (sy[a] != sy[b]) return sy[a] < sy[b];
        return a < b;
    });

    // 2–4. Split into K blocks; each block -> one hub at centroid
    long double C_base = 0.0L;
    for (int t = 1; t <= K; t++) {
        int lo = (int)((long long)(t - 1) * N / K);
        int hi = (int)((long long)t       * N / K);
        if (lo >= hi) continue;   // empty block – skip

        int cnt = hi - lo;
        long double mx = 0.0L, my = 0.0L;
        for (int i = lo; i < hi; i++) {
            mx += sx[order[i]];
            my += sy[order[i]];
        }
        mx /= (long double)cnt;
        my /= (long double)cnt;

        long double br2 = 0.0L, bl = 0.0L;
        for (int i = lo; i < hi; i++) {
            int j = order[i];
            long double dx = mx - sx[j];
            long double dy = my - sy[j];
            long double d2 = dx * dx + dy * dy;
            if (d2 > br2) br2 = d2;
            bl += sd[j];
        }
        C_base += P + A * br2 + B * bl * bl;
    }

    // ── Score = 1e6 * C_base / (C_base + C) ────────────────────────────────
    // ratio is in [0, 1]; the platform multiplies by 1e6 to get the per-test score.
    // ratio = 0.5 => score 500000 (matches baseline)
    // ratio > 0.5 => better than baseline
    // ratio < 0.5 => worse than baseline
    long double ratio = 0.0L;
    if (C_base + C > 0.0L)
        ratio = C_base / (C_base + C);
    if (ratio < 0.0L) ratio = 0.0L;
    if (ratio > 1.0L) ratio = 1.0L;

    // quitp expects a value in [0,1]; the platform scales by 1e6 for the per-test score.
    // The "Ratio:" tag is parsed by the orchestrator.
    quitp((double)ratio,
          "Ratio: %.9Lf | C=%.9Lf C_base=%.9Lf",
          ratio, C, C_base);

    return 0;
}