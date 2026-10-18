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

#include <vector>
#include <iostream>
#include <iomanip>

using namespace std;


const int LIMIT_BASE = 100000;
const int LIMIT_ZERO = 400000;

const int MAXN = 80005;
const int LOGK = 18;

vector<int> adj[MAXN];
int up[LOGK][MAXN];
int depth[MAXN];
int queries = 0;

void dfs(int u, int p, int d) {
    depth[u] = d;
    up[0][u] = p;
    for (int v : adj[u]) {
        if (v != p) {
            dfs(v, u, d + 1);
        }
    }
}

void precompute_lca(int n) {
    dfs(1, 1, 0);
    for (int k = 1; k < LOGK; ++k) {
        for (int i = 1; i <= n; ++i) {
            up[k][i] = up[k - 1][up[k - 1][i]];
        }
    }
}

int get_lca(int u, int v) {
    if (depth[u] < depth[v]) swap(u, v);
    for (int k = LOGK - 1; k >= 0; --k) {
        if (depth[u] - (1 << k) >= depth[v]) {
            u = up[k][u];
        }
    }
    if (u == v) return u;
    for (int k = LOGK - 1; k >= 0; --k) {
        if (up[k][u] != up[k][v]) {
            u = up[k][u];
            v = up[k][v];
        }
    }
    return up[0][u];
}

int get_dist(int u, int v) {
    return depth[u] + depth[v] - 2 * depth[get_lca(u, v)];
}

int main(int argc, char* argv[]) {
    setName("Interactor for Centroid Guess with Bounded/Unbounded Scoring");
    registerInteraction(argc, argv);

    int n = inf.readInt(3, 75000, "n");

    for (int i = 0; i < n - 1; ++i) {
        int u = inf.readInt(1, n, "u");
        int v = inf.readInt(1, n, "v");
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    int expected_centroid = ans.readInt(1, n, "centroid");

    precompute_lca(n);

    cout << n << endl;

    int safety_limit = LIMIT_ZERO + 10000;
    bool solved = false;

    while (!solved) {
        string type = ouf.readToken("[?!]");

        if (type == "?") {
            queries++;
            if (queries > safety_limit) {
                quitf(_wa, "Safety query limit exceeded (> %d)", safety_limit);
            }

            int u = ouf.readInt(1, n, "query_u");
            int v = ouf.readInt(1, n, "query_v");

            int dist = get_dist(u, v);
            cout << dist << endl;
        }
        else if (type == "!") {
            int user_ans = ouf.readInt(1, n, "user_answer");

            if (user_ans == expected_centroid) {
                solved = true;
            } else {
                quitf(_wa, "Wrong answer. Expected %d, found %d.", expected_centroid, user_ans);
            }
        }
    }

    double L = (double)LIMIT_ZERO;
    double O = (double)LIMIT_BASE;

    double r = max(0.0, (L - queries) / (L - O));
    double bounded_score = reference_score(r * r);
    bounded_score = natural_log_score(100.0 * bounded_score, queries, O, true) / 100.0;
    double unbounded_score = bounded_score;

    quitp(bounded_score,
          "Queries: %d. Ratio: %.12f, RatioUnbounded: %.12f",
          queries, bounded_score, unbounded_score);

    return 0;
}
