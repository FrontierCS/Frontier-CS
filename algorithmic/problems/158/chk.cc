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


// Legacy base ratio, retained only to decide and preserve the lower band.
static double penalized(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    long long N = inf.readLong();
    int K = inf.readInt();
    vector<long long> a(10);
    for (int i = 0; i < 10; i++) a[i] = inf.readLong();
    vector<long long> xs(N), ys(N);
    for (long long i = 0; i < N; i++) {
        xs[i] = inf.readLong();
        ys[i] = inf.readLong();
    }

    // Parse outputs: multiple solutions allowed, only the last one is used
    struct Line { long long px, py, qx, qy; };
    vector<vector<Line>> solutions;
    while (!ouf.seekEof()) {
        int k = ouf.readInt(0, K, "k");
        vector<Line> lines;
        lines.reserve(k);
        for (int i = 0; i < k; i++) {
            long long px = ouf.readLong(-1000000000LL, 1000000000LL, "px");
            long long py = ouf.readLong(-1000000000LL, 1000000000LL, "py");
            long long qx = ouf.readLong(-1000000000LL, 1000000000LL, "qx");
            long long qy = ouf.readLong(-1000000000LL, 1000000000LL, "qy");
            ouf.ensuref(!(px == qx && py == qy), "line endpoints must be different (got identical points at cut %d)", i + 1);
            lines.push_back({px, py, qx, qy});
        }
        solutions.push_back(lines);
    }

    ouf.ensuref(!solutions.empty(), "no solution provided");

    // Use the last solution
    const vector<Line>& lines = solutions.back();

    // Compute pieces
    vector<vector<int>> pieces(1);
    pieces[0].resize(N);
    iota(pieces[0].begin(), pieces[0].end(), 0);

    for (const auto& ln : lines) {
        vector<vector<int>> new_pieces;
        new_pieces.reserve(pieces.size() * 2);
        long long px = ln.px, py = ln.py, qx = ln.qx, qy = ln.qy;
        long long vx = qx - px, vy = qy - py;

        for (auto& piece : pieces) {
            vector<int> left, right;
            left.reserve(piece.size());
            right.reserve(piece.size());

            for (int idx : piece) {
                long long x = xs[idx], y = ys[idx];
                long long sx = x - px, sy = y - py;
                __int128 cross = (__int128)vx * (__int128)sy - (__int128)vy * (__int128)sx;
                if (cross > 0) {
                    left.push_back(idx);
                } else if (cross < 0) {
                    right.push_back(idx);
                } else {
                    // on the line -> discarded
                }
            }
            if (!left.empty()) new_pieces.push_back(move(left));
            if (!right.empty()) new_pieces.push_back(move(right));
        }
        pieces.swap(new_pieces);
    }

    // Count b_d
    vector<long long> b(10, 0);
    for (const auto& piece : pieces) {
        size_t sz = piece.size();
        if (sz >= 1 && sz <= 10) b[sz - 1]++;
    }

    // Compute score
    long long num = 0;
    long long den = 0;
    for (int d = 0; d < 10; d++) {
        num += min<long long>(a[d], b[d]);
        den += a[d];
    }
    ensuref(den > 0, "invalid input: sum of a_d is zero");
    long long score = llround(1e6 * (double)num / (double)den);

    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = 0.6 * calibration_ratio;
    // Matching every requested piece is a genuine mathematical maximum.
    if (best_value == 1000000) score_ratio = penalized(calibration_ratio);
    score_ratio = natural_log_score(100.0 * score_ratio, num, (long double)den * (best_value == 1000000 ? (long double)baseline_value + 0.6L*gap : (long double)best_value) / 1e6L, false) / 100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
}
