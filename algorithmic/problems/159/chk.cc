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

struct Point { int x, y; };

static inline int sgn(long long v) {
    if (v < 0) return -1;
    if (v > 0) return 1;
    return 0;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    int N = inf.readInt();
    int M = inf.readInt();
    vector<Point> initial(M);
    for (int i = 0; i < M; i++) {
        initial[i].x = inf.readInt();
        initial[i].y = inf.readInt();
    }

    // State initialization
    vector<vector<bool>> has_point(N, vector<bool>(N, false));
    for (const auto& p : initial) {
        if (p.x < 0 || p.x >= N || p.y < 0 || p.y >= N) {
            quitf(_wa, "Initial point out of range: (%d, %d)", p.x, p.y);
        }
        has_point[p.x][p.y] = true;
    }
    // used[x][y][dir], dir in 0..7 as in DXY
    const int DXY[8][2] = {
        {1, 0},
        {1, 1},
        {0, 1},
        {-1, 1},
        {-1, 0},
        {-1, -1},
        {0, -1},
        {1, -1},
    };
    vector<vector<array<bool, 8>>> used(N, vector<array<bool, 8>>(N));
    for (int x = 0; x < N; x++) for (int y = 0; y < N; y++) used[x][y].fill(false);

    // Read output
    long long K = ouf.readLong(0, 1000000000LL, "K");
    vector<array<Point, 4>> rects;
    rects.reserve((size_t)min<long long>(K, 1000000)); // reserve some, but not necessary

    for (long long t = 0; t < K; t++) {
        array<Point, 4> r;
        for (int i = 0; i < 4; i++) {
            r[i].x = ouf.readInt(0, N - 1, "x");
            r[i].y = ouf.readInt(0, N - 1, "y");
        }

        // Check move legality (following Rust checker)
        // Ensure p2,p3,p4 contain dots; p1 does not contain a dot
        for (int i = 1; i <= 3; i++) {
            if (!has_point[r[i].x][r[i].y]) {
                quitf(_wa, "(%d, %d) does not contain a dot (turn: %lld)", r[i].x, r[i].y, t);
            }
        }
        if (has_point[r[0].x][r[0].y]) {
            quitf(_wa, "(%d, %d) already contains a dot (turn: %lld)", r[0].x, r[0].y, t);
        }

        long long dx01 = r[1].x - r[0].x;
        long long dy01 = r[1].y - r[0].y;
        long long dx03 = r[3].x - r[0].x;
        long long dy03 = r[3].y - r[0].y;

        if (dx01 * dx03 + dy01 * dy03 != 0) {
            quitf(_wa, "Illegal rectangle: edges are not perpendicular (turn: %lld)", t);
        }
        if (dx01 != 0 && dy01 != 0 && llabs(dx01) != llabs(dy01)) {
            quitf(_wa, "Illegal rectangle: not axis-aligned or 45 degrees (turn: %lld)", t);
        }
        if (!(r[2].x == r[1].x + dx03 && r[2].y == r[1].y + dy03)) {
            quitf(_wa, "Illegal rectangle: wrong 4th point (turn: %lld)", t);
        }

        // Check edges: obstacles and overlapping
        for (int i = 0; i < 4; i++) {
            int x = r[i].x, y = r[i].y;
            int tx = r[(i + 1) % 4].x, ty = r[(i + 1) % 4].y;
            int dx = sgn(tx - x), dy = sgn(ty - y);

            int dir = -1;
            for (int d = 0; d < 8; d++) {
                if (DXY[d][0] == dx && DXY[d][1] == dy) { dir = d; break; }
            }
            if (dir == -1) {
                quitf(_wa, "Illegal edge direction (turn: %lld)", t);
            }

            // Step along the edge from (x,y) to (tx,ty)
            while (x != tx || y != ty) {
                if (!(x == r[i].x && y == r[i].y)) {
                    if (has_point[x][y]) {
                        quitf(_wa, "There is an obstacle at (%d, %d) (turn: %lld)", x, y, t);
                    }
                }
                if (used[x][y][dir]) {
                    quitf(_wa, "Overlapped rectangles (turn: %lld)", t);
                }
                x += dx; y += dy;
                if (used[x][y][dir ^ 4]) {
                    quitf(_wa, "Overlapped rectangles (turn: %lld)", t);
                }
            }
        }

        // Apply move
        has_point[r[0].x][r[0].y] = true;
        for (int i = 0; i < 4; i++) {
            int x = r[i].x, y = r[i].y;
            int tx = r[(i + 1) % 4].x, ty = r[(i + 1) % 4].y;
            int dx = sgn(tx - x), dy = sgn(ty - y);

            int dir = -1;
            for (int d = 0; d < 8; d++) {
                if (DXY[d][0] == dx && DXY[d][1] == dy) { dir = d; break; }
            }
            // dir must be valid due to previous checks
            while (x != tx || y != ty) {
                used[x][y][dir] = true;
                x += dx; y += dy;
                used[x][y][dir ^ 4] = true;
            }
        }

        rects.push_back(r);
    }

    // Ensure no extra tokens (optional)
    ouf.seekEof();

    auto weight = [&](int x, int y) -> long long {
        long long cx = N / 2;
        long long dx = x - cx;
        long long dy = y - cx;
        return dx * dx + dy * dy + 1;
    };

    // Compute score
    long long num = 0;
    for (const auto& p : initial) {
        num += weight(p.x, p.y);
    }
    for (const auto& r : rects) {
        num += weight(r[0].x, r[0].y);
    }
    long long den = 0;
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) den += weight(i, j);

    double scoreD = (1e6 * (double)(N * N) / (double)M) * ((double)num / (double)den);
    long long score = llround(scoreD);

    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = calibration_ratio <= 1.0 ? 0.6 * calibration_ratio : 0.6 + 0.02 * log(calibration_ratio);
    score_ratio = natural_log_score(100.0 * score_ratio, num, (long double)best_value * M * den / (1e6L * N * N), false) / 100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
}
