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

// Reference calibration: 60 points at r=1, logarithmic rewards above it.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}
using namespace std;

double F_bounded(int x, int n) {
    return natural_log_score(100.0 * calibrated((n + 1000.0 - x) / 1000.0), x, n, true);
}
double F_unbounded(int x, int n) { return F_bounded(x,n); }

int rt, a[1005], fa[1005], f[1005];
vector<int> g[1005];

void dfs(int x){
    f[x] += a[x];
    for (auto i : g[x]) if (i != fa[x]) {
        fa[i] = x;
        f[i] = f[x];
        dfs(i);
    }
}

void mdf(int x){
    f[x] -= a[x];
    a[x] = 0 - a[x];
    dfs(x);
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    int T = inf.readInt();
    cout << T << endl;

    double best_bounded = std::numeric_limits<double>::infinity();
    double best_unbounded = std::numeric_limits<double>::infinity();
    int mxq = 0;

    uint32_t seed = static_cast<uint32_t>(
        chrono::steady_clock::now().time_since_epoch().count()
    );
    mt19937 rnd(seed);

    for (int tc = 0; tc < T; tc++) {
        int n = inf.readInt();

        cout << n << endl;

        for (int i = 1; i <= n; i++) {
            g[i].clear();
            a[i] = (rnd() & 1) ? 1 : -1;
            fa[i] = 0; f[i] = 0;
        }
        for (int i = 1; i < n; i++) {
            int x = inf.readInt(1, n);
            int y = inf.readInt(1, n);
            ensuref(x != y, "edge endpoints must differ");
            cout << x << " " << y << endl;
            g[x].push_back(y);
            g[y].push_back(x);
        }
        rt = inf.readInt(1, n);
        dfs(rt);

        int queries = 0;
        while (true) {
            string op = ouf.readToken();
            if (op == "?") {
                queries++;
                int op1 = ouf.readInt(1, 2, "op1");
                if (op1 == 1) {
                    int m = ouf.readInt(1, n, "m");
                    long long res = 0;
                    for (int i = 1; i <= m; i++) {
                        int x = ouf.readInt(1, n, "x");
                        res += f[x];
                    }
                    cout << res << endl;
                } else if (op1 == 2) {
                    int x = ouf.readInt(1, n, "x");
                    mdf(x);
                } else {
                    quitf(_wa, "unknown command");
                }
            } else if (op == "!") {
                for (int i = 1; i <= n; i++) {
                    int x = ouf.readInt(-1, 1, "a[i]");
                    ensuref(x == -1 || x == 1, "a[i] must be -1 or 1");
                    if (x != a[i]) {
                        quitf(_wa, "wrong answer");
                    }
                }
                double sc_b = F_bounded(queries, n);
                double sc_u = F_unbounded(queries, n);
                best_bounded   = min(best_bounded, sc_b);
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
