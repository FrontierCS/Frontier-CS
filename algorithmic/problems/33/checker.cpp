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

static string output_secret = "6cad0f33-b1bd-3a3e-1a8d-c4af23adfcbf";

const long long MX = 1e18;
long long bit[5005];
int mx;

void init(int n) {
    for (int i = 0; i <= n + 1; i++)
        bit[i] = 0;
    mx = n + 1;
}

long long add(long long x, long long y) {
    x += y;
    if (x > MX) return MX + 1;
    return x;
}

void update(int ind, long long x) {
    ind++;
    for (; ind <= mx; ind += ind & (-ind))
        bit[ind] = add(bit[ind], x);
}

long long query(int ind) {
    long long ret = 0;
    ind++;
    for (; ind > 0; ind -= ind & (-ind))
        ret = add(ret, bit[ind]);
    return ret;
}

long long getInc(vector<int> perm) {
    int n = (int)perm.size();
    init(n);
    long long ans = 1;
    update(0, 1);
    for (int i = 0; i < n; i++) {
        long long me = query(perm[i] + 1);
        update(perm[i] + 1, me);
        ans = add(ans, me);
    }
    return ans;
}

double score_bounded(int n) {
    if (n <= 90) return 90.0;
    if (n >= 2000) return 0.0;
    return 90.0 * (2000.0 - n) / (2000.0 - 90.0);
}

double score_unbounded(int n) {
    if (n >= 2000) return 0.0;
    return 90.0 * (2000.0 - n) / (2000.0 - 90.0);
}

int main(int argc, char *argv[]) {
    registerTestlibCmd(argc, argv);

    int t = inf.readInt();
    int mxn = 0;

    while (t--) {
        long long k = inf.readLong();
        int n = ouf.readInt(1, 5000, "n");
        vector<int> perm(n);
        set<int> ss;
        for (int i = 0; i < n; i++) {
            perm[i] = ouf.readInt(0, n - 1, "perm[i]");
            ss.insert(perm[i]);
        }
        if ((int)ss.size() != n)
            quitf(_wa, "Permutation contains duplicates");

        long long g = getInc(perm);
        if (g != k)
            quitf(_wa, "Wrong value for getInc");

        mxn = max(mxn, n);
    }

    double bounded = score_bounded(mxn);
    double unbounded = score_unbounded(mxn);

    double score_ratio = calibrated(unbounded / 90.0);
    score_ratio = natural_log_score(100.0 * score_ratio, mxn, 90, true) / 100.0;
    double unbounded_ratio = score_ratio;

    quitp(score_ratio, "Value: %d. Ratio: %.12f, RatioUnbounded: %.12f",
          mxn, score_ratio, unbounded_ratio);
}
