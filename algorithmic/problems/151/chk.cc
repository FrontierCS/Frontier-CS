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

struct InputData {
    int N;
    int si, sj;
    vector<string> c;
};

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    InputData in;
    in.N = inf.readInt();
    in.si = inf.readInt();
    in.sj = inf.readInt();
    in.c.resize(in.N);
    for (int i = 0; i < in.N; i++) {
        in.c[i] = inf.readToken();
        if ((int)in.c[i].size() != in.N) {
            quitf(_wa, "Invalid input line length");
        }
    }

    // Read output: allow empty output, but not more than one token
    string out;
    if (ouf.seekEof()) {
        out = "";
    } else {
        out = ouf.readToken();
        if (!ouf.seekEof()) {
            quitf(_wa, "Too Many Output");
        }
    }

    // Simulate route
    int pi = in.si, pj = in.sj;
    long long length = 0;
    vector<pair<int,int>> ps;
    ps.emplace_back(pi, pj);

    for (char c : out) {
        int di = 0, dj = 0;
        if (c == 'U') { di = -1; dj = 0; }
        else if (c == 'D') { di = 1; dj = 0; }
        else if (c == 'L') { di = 0; dj = -1; }
        else if (c == 'R') { di = 0; dj = 1; }
        else {
            // Illegal character
            string msg = "Illegal output: ";
            msg.push_back(c);
            quitf(_wa, "%s", msg.c_str());
        }
        pi += di;
        pj += dj;
        if (pi < 0 || pi >= in.N || pj < 0 || pj >= in.N || in.c[pi][pj] == '#') {
            quitf(_wa, "Visiting an obstacle");
        }
        length += (in.c[pi][pj] - '0');
        ps.emplace_back(pi, pj);
    }

    // Compute visibility
    vector<vector<bool>> vis(in.N, vector<bool>(in.N, false));
    auto markVisibilityFrom = [&](int ci, int cj) {
        // Up
        for (int i = ci; i >= 0; --i) {
            if (in.c[i][cj] == '#') break;
            vis[i][cj] = true;
        }
        // Down
        for (int i = ci; i < in.N; ++i) {
            if (in.c[i][cj] == '#') break;
            vis[i][cj] = true;
        }
        // Left
        for (int j = cj; j >= 0; --j) {
            if (in.c[ci][j] == '#') break;
            vis[ci][j] = true;
        }
        // Right
        for (int j = cj; j < in.N; ++j) {
            if (in.c[ci][j] == '#') break;
            vis[ci][j] = true;
        }
    };
    for (auto &p : ps) markVisibilityFrom(p.first, p.second);

    // Check return to start
    if (ps.back().first != in.si || ps.back().second != in.sj) {
        quitf(_wa, "You have to go back to the starting point");
    }

    // Compute score
    long long num = 0, den = 0;
    for (int i = 0; i < in.N; i++) {
        for (int j = 0; j < in.N; j++) {
            if (in.c[i][j] != '#') {
                den++;
                if (vis[i][j]) num++;
            }
        }
    }

    double score = 1e4 * (double)num / (double)den;
    if (num == den) {
        // length should be > 0 if full coverage is achieved
        if (length <= 0) {
            quitf(_wa, "Invalid length for full coverage");
        }
        score += 1e7 * (double)in.N / (double)length;
    }
    long long finalScore = llround(score);
    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)finalScore - (double)baseline_value) / gap);
    double score_ratio = 0.6 * calibration_ratio;
    if (num == den && best_value > 10000) {
        score_ratio = natural_log_score(100.0 * score_ratio, length, 1e7L * in.N / (best_value - 10000.0L), true) / 100.0;
    } else {
        score_ratio = natural_log_score(100.0 * score_ratio, finalScore, best_value, false) / 100.0;
    }
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", finalScore, score_ratio, score_ratio);
}
