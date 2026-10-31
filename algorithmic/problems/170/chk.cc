#include <cmath>
#include <algorithm>

// Scores are in points here. Preserve the previous lower band, and compare
// the original objective with its 60-point anchor using the natural logarithm.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0) return old_points;
    // A zero reference or a flat legacy score has no positive logarithmic anchor.
    if (!(value > 0.0L) || !(anchor > 0.0L)) return old_points;
    const long double gain = minimize ? std::log(anchor) - std::log(value)
                                      : std::log(value) - std::log(anchor);
    return static_cast<double>(std::min(100.0L, 60.0L + gain));
}

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    long long n = inf.readLong();
    long long l = inf.readLong();
    vector<long long> T = inf.readLongs((int)n);

    // Read output pairs until EOF
    vector<pair<long long, long long>> out;
    while (!ouf.seekEof()) {
        long long a = ouf.readLong(0, n - 1);
        long long b = ouf.readLong(0, n - 1);
        out.emplace_back(a, b);
    }

    if ((long long)out.size() != n) {
        quitf(_wa, "Number of pairs in output is not N");
    }

    // Simulation
    vector<long long> counts(n, 0);
    long long pos = 0;
    for (long long step = 0; step < l; ++step) {
        long long a = out[pos].first;
        long long b = out[pos].second;
        counts[pos] += 1;
        if (counts[pos] % 2 == 1) pos = a;
        else pos = b;
    }

    // Score calculation: score = 2 * L - sum |counts[i] - T[i]|
    long long score = 2LL * l;
    for (long long i = 0; i < n; ++i) {
        long long diff = counts[i] - T[i];
        score -= llabs(diff);
    }

    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = 0.6 * calibration_ratio;
    score_ratio = natural_log_score(100.0 * score_ratio, 2LL*l-score, 2.0L*l-best_value, true) / 100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
}
