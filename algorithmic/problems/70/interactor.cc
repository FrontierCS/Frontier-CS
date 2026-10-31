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
#include <vector>
#include <iostream>
#include <iomanip>
#include <random>

// Reference calibration: 60 points at r=1, logarithmic rewards above it.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

using namespace std;

struct Node {
    int id;
    int degree;
    bool visited;
};

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    int t = inf.readInt();
    cout << t << endl;

    double tot_score = 0.0;
    long long tot_moves = 0.0;
    long long tot_base_move_count = 0.0;
    double tot_unbounded_score = 0.0;

    for (int k = 0; k < t; ++k) {
        int n = inf.readInt(2, 300, "n");
        int m = inf.readInt(1, min(n * (n - 1) / 2, 25 * n), "m");
        int start = inf.readInt(1, n, "start");
        int base_move_count = inf.readInt();

        cout << n << " " << m << " " << start << " " << base_move_count << endl;

        vector<vector<int>> adj(n + 1);
        vector<int> degrees(n + 1, 0);

        for (int i = 0; i < m; ++i) {
            int u = inf.readInt(1, n, "u");
            int v = inf.readInt(1, n, "v");
            adj[u].push_back(v);
            adj[v].push_back(u);

            cout << u << " " << v << endl;
        }

        for(int i = 1; i <= n; ++i) {
            degrees[i] = adj[i].size();
        }

        std::mt19937 gen(rnd.next(1, 1000000000));
        int curr = start;
        vector<bool> visited(n + 1, false);
        visited[curr] = true;
        int visited_count = 1;
        int moves = 0;

        long long limit = 2LL * base_move_count;
        bool success = false;

        while (moves <= limit) {
            if (visited_count == n) {
                success = true;
                break;
            }

            if (moves == limit) {
                break;
            }

            vector<int> neighbors = adj[curr];

            std::shuffle(neighbors.begin(), neighbors.end(), gen);

            int d = neighbors.size();
            cout << d;
            for (int neighbor_idx : neighbors) {
                cout << " " << degrees[neighbor_idx] << " " << (visited[neighbor_idx] ? 1 : 0);
            }
            cout << endl;

            int choice = ouf.readInt(1, d, "choice index");

            curr = neighbors[choice - 1];
            moves++;

            if (!visited[curr]) {
                visited[curr] = true;
                visited_count++;
            }
        }

        tot_moves += moves;
        tot_base_move_count += base_move_count;

        if (success) {
            cout << "AC" << endl;

            double r = std::max(0.0, (2.0 * base_move_count - moves) / base_move_count);
            double current_score = calibrated(r * r);
    current_score = natural_log_score(100.0 * current_score, moves, base_move_count, true) / 100.0;
            tot_unbounded_score += current_score;

            tot_score += current_score;
        } else {
            cout << "F" << endl;
        }
    }

    double score_ratio = tot_score / t;
    double unbounded_score_ratio = tot_unbounded_score / t;
    quitp(score_ratio, "Queries: %lld. Ratio: %.12f, RatioUnbounded: %.12f", tot_moves, score_ratio, unbounded_score_ratio);

    return 0;
}
