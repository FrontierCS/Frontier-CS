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
#include "testlib.h"
#include <iostream>
#include <cstring>
#include <algorithm>

using namespace std;
// Historical calibration supplies the unchanged low-score branch.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}
using namespace std;



const int N = 202021;
bool vis[N * 50];
int n, m, L, R, Sx, Sy, qn, q[N], x[N], y[N], vis1[N],stk[N];

int _abs(int x) {
    return (x < 0) ? (-x) : x;
}

inline int get(int x, int y) {
    return (x - 1) * m + y;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input from inf
    n = inf.readInt();
    m = inf.readInt();
    L = inf.readInt();
    R = inf.readInt();
    Sx = inf.readInt();
    Sy = inf.readInt();
    qn = inf.readInt();
    int mxstp = inf.readInt();

    for (int i = 1; i <= qn; i++) {
        q[i] = inf.readInt();
    }

    // Read output from ouf
    string s = ouf.readToken();
    if (s != "YES" && s != "NO") {
        quitf(_wa, "First line must be YES or NO, got: %s", s.c_str());
    }

    if (s == "NO") {
        // Check if solution is actually impossible (we assume checker doesn't verify this)
        // For now, give 0 points if output is NO
        quitp(0.0, "Output is NO, no valid path found");
    }

    long long cnt = ouf.readLong();
    if (cnt > (long long)n * m) {
        quitf(_wa, "Path length %lld exceeds grid size %d * %d", cnt, n, m);
    }

    if (cnt < 1) {
        quitf(_wa, "Path length must be at least 1");
    }

    for (int i = 1; i <= cnt; i++) {
        x[i] = ouf.readInt();
        y[i] = ouf.readInt();
        if (x[i] < 1 || x[i] > n || y[i] < 1 || y[i] > m) {
            quitf(_wa, "Coordinate (%d, %d) at step %d is out of bounds", x[i], y[i], i);
        }
    }

    // Check starting position
    if (x[1] != Sx || y[1] != Sy) {
        quitf(_wa, "Path must start at (%d, %d), but starts at (%d, %d)", Sx, Sy, x[1], y[1]);
    }

    // Check path continuity (each step moves to adjacent cell)
    for (int i = 2; i <= cnt; i++) {
        if (x[i] != x[i-1] && y[i] != y[i-1]) {
            quitf(_wa, "Step %d: must move in exactly one direction (from (%d,%d) to (%d,%d))",
                  i, x[i-1], y[i-1], x[i], y[i]);
        }
        if (_abs(x[i] - x[i-1]) > 1 || _abs(y[i] - y[i-1]) > 1) {
            quitf(_wa, "Step %d: can only move one step (from (%d,%d) to (%d,%d))",
                  i, x[i-1], y[i-1], x[i], y[i]);
        }
    }

    // Check no cell is visited twice
    memset(vis, 0, sizeof(vis));
    for (int i = 1; i <= cnt; i++) {
        int pos = get(x[i], y[i]);
        if (vis[pos]) {
            quitf(_wa, "Cell (%d, %d) is visited multiple times", x[i], y[i]);
        }
        vis[pos] = true;
    }

    // Check all required areas are visited
    for (int i = 1; i <= n; i++) {
        for (int j = L; j <= R; j++) {
            if (!vis[get(i, j)]) {
                quitf(_wa, "Required cell (%d, %d) is not visited", i, j);
            }
        }
    }

    // Check row completion constraint
    memset(vis1, 0, sizeof(vis1));
    int top=0;
    for (int i = 1; i <= cnt; i++) {
        if (y[i] < L || y[i] > R) continue;
        if (vis1[x[i]]) continue;
        vis1[x[i]] = 1;
        stk[++top]=x[i];
        // When first entering row x[i]'s required area, must complete all required cells in that row
        for (int j = L; j <= R; j++) {
            int idx = j - L + i;
            if (idx > cnt) break;
            if(x[idx] != x[i])
            	quitf(_wa, "Row %d: after entering required area, cannot leave before completing all required cells", x[i]);
            if (y[idx] < L || y[idx] > R) {
                quitf(_wa, "Row %d: after entering required area, cannot leave before completing all required cells", x[i]);
            }
        }
    }

    if(top!=n)
    	quitf(_wa, "Required cell is not visited");
    int nw=1;
    for(int i=1;i<=qn;i++){
    	while(nw<=top && q[i]!=stk[nw])++nw;
    	if(stk[nw]!=q[i])quitf(_wa, "Your clearance sequence does not contain the required subsequence");
    }
    double r = std::max(0.0, 1.0 - (double(cnt) - mxstp) / (10.0 * n));
    double score_ratio = calibrated(r);
    score_ratio = natural_log_score(100.0L * (score_ratio), cnt, mxstp, true) / 100.0;
    double unbounded_ratio = score_ratio;
    double points = 100.0 * score_ratio;

    quitp(score_ratio, "Value: %.12f. Ratio: %.12f, RatioUnbounded: %.12f", points, score_ratio, unbounded_ratio);

    return 0;
}
