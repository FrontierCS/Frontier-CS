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

static inline bool parsePositiveLL(const string& s, long long& out) {
    if (s.empty()) return false;
    long long val = 0;
    for (char c : s) {
        if (c < '0' || c > '9') return false;
        int d = c - '0';
        val = val * 10 + d;
        if (val > (long long)1e18) return false; // safety
    }
    out = val;
    return true;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    int N = inf.readInt();
    vector<vector<long long>> h(N, vector<long long>(N));
    long long base = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            h[i][j] = inf.readLong();
            base += llabs(h[i][j]);
        }
    }

    // Simulation state
    long long i = 0, j = 0;     // current position
    long long v = 0;            // loaded soil
    long long cost = 0;         // total cost

    // Parse output lines
    int actions = 0;
    while (!ouf.seekEof()) {
        string line = ouf.readLine();
        line = ::trim(line);
        if (line.empty()) continue;

        ++actions;
        if (actions > 100000) {
            quitf(_wa, "Too many actions");
        }

        if (line.size() == 1) {
            char c = line[0];
            if (c == 'U' || c == 'D' || c == 'L' || c == 'R') {
                // Move
                if (c == 'U') --i;
                else if (c == 'D') ++i;
                else if (c == 'L') --j;
                else if (c == 'R') ++j;

                if (i < 0 || i >= N || j < 0 || j >= N) {
                    quitf(_wa, "Out of the board. (turn: %d)", actions - 1);
                }
                cost += llabs(v) + 100;
            } else {
                quitf(_wa, "Invalid action: %s", line.c_str());
            }
        } else if (!line.empty() && (line[0] == '+' || line[0] == '-')) {
            if (line.size() == 1) {
                quitf(_wa, "Invalid action: %s", line.c_str());
            }
            string num = line.substr(1);
            long long dpos;
            if (!parsePositiveLL(num, dpos)) {
                quitf(_wa, "Parse error: %s", num.c_str());
            }
            if (dpos < 1 || dpos > 1000000) {
                quitf(_wa, "Out of range: %s", num.c_str());
            }
            long long d = (line[0] == '-') ? -dpos : dpos;

            if (d < 0) {
                if (v + d < 0) {
                    quitf(_wa, "The unloading amount exceeds the carrying amount. (turn: %d)", actions - 1);
                }
                v += d;
                h[i][j] -= d; // unload increases height
            } else {
                v += d;
                h[i][j] -= d; // load decreases height
            }
            cost += llabs(d);
        } else {
            quitf(_wa, "Invalid action: %s", line.c_str());
        }
    }

    // Compute diff
    long long diff = 0;
    for (int ii = 0; ii < N; ++ii) {
        for (int jj = 0; jj < N; ++jj) {
            if (h[ii][jj] != 0) {
                diff += 10000 + 100LL * llabs(h[ii][jj]);
            }
        }
    }

    long long denom = cost + diff;
    long long score = 0;
    if (denom > 0) {
        long double val = (1e9L * (long double)base) / (long double)denom;
        score = llround(val);
    }

    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = calibration_ratio <= 1.0 ? 0.6 * calibration_ratio : 0.6 + 0.02 * log(calibration_ratio);
    score_ratio = natural_log_score(100.0 * score_ratio, denom, best_value > 0 ? 1e9L * base / best_value : 0.0L, true) / 100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
}
