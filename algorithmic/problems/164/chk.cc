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
    long long m = inf.readLong();
    vector<vector<long long>> stacks(m);
    long long h = n / m;
    for (long long i = 0; i < m; ++i) {
        stacks[i].resize(h);
        for (long long j = 0; j < h; ++j) {
            stacks[i][j] = inf.readLong(1, n);
        }
    }

    // Read output
    vector<pair<long long, long long>> ops;
    while (!ouf.seekEof()) {
        long long v = ouf.readLong(1, n);
        long long to = ouf.readLong(0, m);
        ops.emplace_back(v, to);
        if ((int)ops.size() > 5000) {
            quitf(_wa, "Too many output");
        }
    }

    // Simulate
    long long cost = 0;
    long long t = 0; // number of boxes taken out
    for (auto [v, to] : ops) {
        // Find box v
        long long fi = -1, fj = -1;
        for (long long i = 0; i < m; ++i) {
            for (long long j = 0; j < (long long)stacks[i].size(); ++j) {
                if (stacks[i][j] == v) {
                    fi = i;
                    fj = j;
                    break;
                }
            }
            if (fi != -1) break;
        }
        if (fi == -1) {
            quitf(_wa, "Box %lld has already been taken out.", v);
        }

        if (to == 0) {
            // Operation 2: carry out box v
            if (fj + 1 != (long long)stacks[fi].size()) {
                quitf(_wa, "Box %lld is not at the top of the stack.", v);
            }
            if (v != t + 1) {
                quitf(_wa, "Before carrying out box %lld, all boxes less than %lld must be carried out.", v, v);
            }
            stacks[fi].pop_back();
            ++t;
        } else {
            // Operation 1: move v and above to stack 'to'
            long long len = (long long)stacks[fi].size();
            cost += (len - fj) + 1; // k + 1, where k = len - fj

            long long toidx = to - 1; // convert to 0-based
            if (fi != toidx) {
                // move segment [fj, len)
                auto &src = stacks[fi];
                auto &dst = stacks[toidx];
                for (long long k = fj; k < len; ++k) dst.push_back(src[k]);
                src.resize(fj);
            }
            // if fi == toidx, nothing changes but energy is still expended
        }
    }

    if (t < n) {
        quitf(_wa, "Not finished (%lld / %lld)", t, n);
    }

    long long score = 10000 - cost;
    if (score < 1) score = 1;
    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = calibration_ratio <= 1.0 ? 0.6 * calibration_ratio : 0.6 + 0.01 * log(calibration_ratio);
    score_ratio = natural_log_score(100.0 * score_ratio, cost, best_value >= 1 ? 10000.0L - best_value : 0.0L, true) / 100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
}
