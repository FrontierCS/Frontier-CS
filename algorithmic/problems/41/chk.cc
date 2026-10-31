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
// Performance anchor: 60 points; logarithmic credit above it.
static double reference_score(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6*r : 0.6 + 0.02*std::log(r);
}

#include <bits/stdc++.h>
using namespace std;

typedef long long LL;
typedef __int128 int128;

LL gcd(LL x, LL y){
    if (y) return gcd(y, x % y);
    return x;
}

int main(int argc, char** argv) {
    registerTestlibCmd(argc, argv);

    // Read input: single integer n (1 <= n <= 1e12)
    long long n = inf.readLong();

    // Read contestant output
    int k = ouf.readInt(1, 1000000, "k");
    vector<long long> a(k);
    for (int i = 0; i < k; i++) {
        a[i] = ouf.readLong(1LL, n, "a[i]");
    }

    // Validate contestant sequence
    bool ok = true;
    string reason;

    // strictly increasing
    for (int i = 1; i < k; i++) {
        if (a[i] <= a[i - 1]) {
            ok = false;
            reason = "Sequence is not strictly increasing.";
            break;
        }
    }

    // gcd condition: gcd(a_i, a_{i-1}) > gcd(a_{i-1}, a_{i-2}) for i >= 3
    if (ok && k >= 3) {
        long long g_prev = gcd(a[1], a[0]);
        for (int i = 2; i < k; i++) {
            long long g_now = gcd(a[i], a[i - 1]);
            if (g_now <= g_prev) {
                ok = false;
                reason = "GCDs are not strictly increasing.";
                break;
            }
            g_prev = g_now;
        }
    }

    if (!ok) {
        quitp(0.0, ("Invalid output: " + reason).c_str());
    }

    // Compute contestant value V_you = k * sum(a_i)
    long double sumYou = 0.0L;
    for (long long x : a) sumYou += (long double)x;
    long double V_you = (long double)k * sumYou;

    // If value == 0 (theoretically impossible under valid constraints), score 0
    if (!(V_you > 0.0L)) {
        quitp(0.0, "Invalid: value equals 0.");
    }

    // Read baseline (from standard-output-file) and compute V_base
    int kb = ans.readInt(1, 1000000, "k_base");
    vector<long long> b(kb);
    for (int i = 0; i < kb; i++) {
        b[i] = ans.readLong(1LL, n, "b[i]");
    }

    // Baseline value (assumed valid)
    long double sumBase = 0.0L;
    for (long long x : b) sumBase += (long double)x;
    long double V_base = (long double)kb * sumBase;

    // Fallback to avoid division by zero in pathological baseline
    if (!(V_base > 0.0L)) V_base = 1.0L;

    long double threshold = 1.05 * V_base;
    long double rawRatio = V_you / threshold;
    double ratio = reference_score(rawRatio);
    ratio = natural_log_score(100.0 * ratio, V_you, threshold, false) / 100.0;
    double unbounded_ratio = ratio;

    quitp(ratio, "Ratio: %.12f, RatioUnbounded: %.12f", ratio, unbounded_ratio);
    return 0;
}
