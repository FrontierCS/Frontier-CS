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

static const int DIRS[2][2] = {{0,1},{1,0}};

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    long long N = inf.readLong();
    long long M = inf.readLong();
    vector<string> s(M);
    for (long long i = 0; i < M; i++) {
        s[i] = inf.readToken();
    }

    // Read output matrix
    vector<string> out(N);
    for (long long i = 0; i < N; i++) {
        out[i] = ouf.readToken();
    }
    if (!ouf.seekEof()) {
        quitf(_wa, "Too many lines");
    }

    // Validate output matrix
    long long dotCount = 0;
    for (long long i = 0; i < N; i++) {
        if ((long long)out[i].size() != N) {
            quitf(_wa, "illegal length: %lld", (long long)out[i].size());
        }
        for (long long j = 0; j < N; j++) {
            char c = out[i][j];
            if (!((c >= 'A' && c <= 'H') || c == '.')) {
                quitf(_wa, "illegal char: %c", c);
            }
            if (c == '.') dotCount++;
        }
    }

    auto is_substring = [&](const vector<string>& a, const string& b, long long i, long long j, int d) -> bool {
        int di = DIRS[d][0], dj = DIRS[d][1];
        for (long long k = 0; k < (long long)b.size(); k++) {
            long long ii = (i + di * k) % N;
            long long jj = (j + dj * k) % N;
            if (a[ii][jj] != b[(size_t)k]) return false;
        }
        return true;
    };

    // Compute c = number of strings that appear as a subsequence
    long long c = 0;
    for (long long idx = 0; idx < M; idx++) {
        bool used = false;
        for (long long i = 0; i < N && !used; i++) {
            for (long long j = 0; j < N && !used; j++) {
                for (int d = 0; d < 2 && !used; d++) {
                    if (is_substring(out, s[idx], i, j, d)) {
                        used = true;
                    }
                }
            }
        }
        if (used) c++;
    }

    // Compute score
    double scoreD;
    if (c < M) {
        scoreD = 1e8 * (double)c / (double)M;
    } else {
        double twoNN = 2.0 * (double)N * (double)N;
        scoreD = 1e8 * twoNN / (twoNN - (double)dotCount);
    }
    long long score = llround(scoreD);
    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = calibration_ratio <= 1.0 ? 0.6 * calibration_ratio : 0.6 + 0.02 * log(calibration_ratio);
    // Physical quality keeps full coverage ahead of partial coverage. Once
    // complete, halving the occupied-cell count adds ln(2), without the old
    // reward's 2*N*N-denominator offset or rounding.
    const long double cells = (long double)N * N;
    const long double occupied = cells - dotCount;
    if (c == M && occupied == 0.0L) {
        score_ratio = 1.0;
    } else {
        const long double quality = c < M ? (long double)c / M : cells / occupied;
        const long double occupied_anchor = 2.0L*cells*1e8L/best_value - cells;
        const long double quality_anchor = best_value <= 100000000
            ? (long double)best_value / 1e8L
            : (occupied_anchor > 0.0L ? cells / occupied_anchor : 0.0L);
        score_ratio = natural_log_score(100.0*score_ratio, quality, quality_anchor, false)/100.0;
    }
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
}
