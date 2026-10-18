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

static long long complete_reward_ceiling = 0, complete_reward_floor = 0;
static long long completed_cost = 0;
static bool objective_complete = false;

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

static const int U = 0, D = 1, L = 2, R = 3;
static const char DIRS[4] = {'U','D','L','R'};
static const long long di[4] = {-1, 1, 0, 0};
static const long long dj[4] = {0, 0, -1, 1};

int dir_index(char c) {
    for (int k = 0; k < 4; k++) if (DIRS[k] == c) return k;
    return -1;
}

long long compute_score() {
    // Read input
    long long N = inf.readLong();
    long long M = inf.readLong();
    vector<pair<long long,long long>> ps(M);
    for (long long k = 0; k < M; k++) {
        long long x = inf.readLong();
        long long y = inf.readLong();
        ps[k] = {x, y};
    }

    // Parse output
    struct Action { char a; int d; };
    vector<Action> out;
    while (!ouf.seekEof()) {
        string as = ouf.readToken();
        if (as.size() != 1) quitf(_wa, "Invalid action: %s", as.c_str());
        char a = as[0];
        if (a != 'M' && a != 'S' && a != 'A') quitf(_wa, "Invalid action: %c", a);

        if (ouf.seekEof()) quitf(_wa, "Unexpected EOF after action");
        string ds = ouf.readToken();
        if (ds.size() != 1) quitf(_wa, "Invalid direction: %s", ds.c_str());
        char dc = ds[0];
        int d = dir_index(dc);
        if (d == -1) quitf(_wa, "Invalid direction: %c", dc);

        out.push_back({a, d});
        if ((long long)out.size() > 2LL * N * M) {
            quitf(_wa, "Too many actions: %lld", (long long)out.size());
        }
    }

    // Simulate
    long long pi = ps[0].first;
    long long pj = ps[0].second;
    long long done = 1;
    vector<vector<char>> block((size_t)N, vector<char>((size_t)N, 0));

    auto in_range = [&](long long x, long long y) -> bool {
        return (0 <= x && x < N && 0 <= y && y < N);
    };

    for (size_t t = 0; t < out.size(); t++) {
        char a = out[t].a;
        int d = out[t].d;
        if (a == 'M') {
            long long ni = pi + di[d];
            long long nj = pj + dj[d];
            if (!in_range(ni, nj)) {
                quitf(_wa, "Out of range (M %c)", DIRS[d]);
            }
            if (block[(size_t)ni][(size_t)nj]) {
                quitf(_wa, "Blocked (M %c)", DIRS[d]);
            }
            pi = ni; pj = nj;
        } else if (a == 'S') {
            while (true) {
                long long ni = pi + di[d];
                long long nj = pj + dj[d];
                if (!in_range(ni, nj)) break;
                if (block[(size_t)ni][(size_t)nj]) break;
                pi = ni; pj = nj;
            }
        } else if (a == 'A') {
            long long ai = pi + di[d];
            long long aj = pj + dj[d];
            if (!in_range(ai, aj)) {
                quitf(_wa, "Out of range (A %c)", DIRS[d]);
            }
            block[(size_t)ai][(size_t)aj] ^= 1;
        }

        if (done < M && ps[(size_t)done].first == pi && ps[(size_t)done].second == pj) {
            done++;
        }
    }

    long long score;
    if (done < M) {
        score = done;
    } else {
        score = M + 2LL * N * M - (long long)out.size();
        objective_complete = true;
        completed_cost = out.size();
        complete_reward_ceiling = M + 2LL*N*M;
        complete_reward_floor = M;
    }
    return score;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);
    long long score = compute_score();
    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = 0.6 * calibration_ratio;
    if (objective_complete && completed_cost == 0) score_ratio = 1.0;
    else if (objective_complete && best_value >= complete_reward_floor && best_value < complete_reward_ceiling) {
        score_ratio = natural_log_score(100.0*score_ratio, completed_cost, (long double)complete_reward_ceiling-best_value, true)/100.0;
    } else score_ratio = natural_log_score(100.0*score_ratio, score, best_value, false)/100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
}
