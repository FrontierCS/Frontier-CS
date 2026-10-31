#include <cmath>
#include <algorithm>

// Natural-log calibration above the previous 60-point threshold.
// Keep validation and low scores; an exact zero minimization cost earns 100.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0 || !(value > 0.0L) || !(anchor > 0.0L))
        return old_points;
    const long double delta = minimize ? std::log(anchor) - std::log(value)
                                       : std::log(value) - std::log(anchor);
    return (double)std::min(100.0L, 60.0L + delta);
}

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
static double referenceScore(double r) { return r <= 1.0 ? 0.6*r : 0.6 + 0.02*std::log(r); }


double f_bounded(int x) {
    if (x >= 5000) return 0.0;
    return natural_log_score(100.0 * referenceScore((5000.0 - x) / (5000.0 - 500.0)), x, 500, true);
}

double f_unbounded(int x) {
    if (x >= 5000) return 0.0;
    return natural_log_score(100.0 * referenceScore((5000.0 - x) / (5000.0 - 500.0)), x, 500, true);
}

int a[605], t[305];

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    const int T = 20;
    cout << T << endl;

    double best_bounded = 100.0;
    double best_unbounded = 100.0;
    int mxq = 0;

    uint32_t seed = static_cast<uint32_t>(
        chrono::steady_clock::now().time_since_epoch().count()
    );
    std::mt19937 rnd(seed);

    for (int tc = 0; tc < T; tc++) {
        int n = 300;
        int pos = static_cast<int>(rnd() % n) + 1;

        int tot = 0;
        for (int i = 1; i <= n; i++) a[++tot] = i;
        for (int i = 1; i < pos; i++) a[++tot] = i;
        for (int i = pos + 1; i <= n; i++) a[++tot] = i;
        assert(tot == 2 * n - 1);
        shuffle(a + 1, a + tot + 1, rnd);

        cout << n << endl;

        int queries = 0;
        while (true) {
            string op = ouf.readToken();
            if (op == "?") {
                int x = ouf.readInt(1, n, "x");
                int m = ouf.readInt(1, 2 * n - 1, "m");
                bool flag = false;
                for (int i = 1; i <= m; i++) {
                    int nw = ouf.readInt(1, 2 * n - 1, "idx");
                    if (a[nw] == x) flag = true;
                }
                cout << (flag ? 1 : 0) << endl;
                queries++;
                if (queries > 5000) quitf(_wa, "Too many queries (>5000)");
            } else if (op == "!") {
                int x = ouf.readInt(1, n, "answer");
                if (x != pos) {
                    quitf(_wa, "wrong position on test %d: expected %d, got %d",
                          tc + 1, pos, x);
                }
                double sc_b = f_bounded(queries);
                double sc_u = f_unbounded(queries);
                best_bounded = min(best_bounded, sc_b);
                best_unbounded = min(best_unbounded, sc_u);
                mxq = max(mxq, queries);
                break;
            } else {
                quitf(_pe, "unknown command '%s' on test %d", op.c_str(), tc + 1);
            }
        }
    }

    double ratio = best_bounded / 100.0;
    double ratio_unbounded = best_unbounded / 100.0;

    quitp(ratio, "all %d tests passed; Ratio: %.12f; RatioUnbounded: %.12f; mxq = %d",
          T, ratio, ratio_unbounded, mxq);
    return 0;
}
