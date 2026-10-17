#include <cmath>
#include <algorithm>

// Keep historical scores through 60; above the anchor, compare physical objectives.
static double natural_log_score(long double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0L) return (double)std::max(0.0L, old_points);
    if (!(value > 0.0L) || !(anchor > 0.0L))
        return (double)std::clamp(old_points, 0.0L, 100.0L);
    const long double improvement = minimize
        ? std::log(anchor) - std::log(value)
        : std::log(value) - std::log(anchor);
    return (double)std::clamp(60.0L + improvement, 0.0L, 100.0L);
}

#include "testlib.h"
#include <cmath>
#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

const int MAXN = (1 << 12) + 10;


// Map normalized performance to the reference-anchored score, without a cap.
static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : (0.6 + 0.02 * std::log(r));
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input: n vertices (0 to n)
    int n = inf.readInt();
    if (n < 0 || n > (1 << 12)) {
        quitf(_fail, "Invalid input: n = %d (expected 0 to %d)", n, 1 << 12);
    }

    // Read the number of edges used by the standard reference construction
    int mans = ans.readInt();
    ensuref(mans >= 0, "Reference edge count must be nonnegative");

    // Read output: number of edges added
    int mout = ouf.readInt();
    if (mout < 0) {
        quitf(_wa, "Invalid output: number of edges %d is negative", mout);
    }

    // Initialize graph: initially contains edges i -> i+1 for i = 0 to n-1
    vector<vector<int>> G(n + 1, vector<int>(n + 1, 0));
    vector<vector<int>> outgoing(n + 1);
    for (int i = 0; i < n; ++i) {
        G[i][i + 1] = 1;
        outgoing[i].push_back(i + 1);
    }

    // Process each edge addition
    for (int i = 1; i <= mout; ++i) {
        int a = ouf.readInt();
        int b = ouf.readInt();
        int c = ouf.readInt();

        // Validate vertex indices
        if (a < 0 || a > n || b < 0 || b > n || c < 0 || c > n) {
            quitf(_wa, "Invalid vertex index in edge %d: (%d, %d, %d) (expected 0 to %d)", i, a, b, c, n);
        }

        // Check if edges a->b and b->c exist
        if (!G[a][b] || !G[b][c]) {
            quitf(_wa, "Cannot add edge %d->%d: edges %d->%d and %d->%d must both exist", a, c, a, b, b, c);
        }

        // Add edge a->c
        if (!G[a][c]) {
            G[a][c] = 1;
            outgoing[a].push_back(c);
        }
    }

    // Verify that for every pair (i, j) with i < j, there exists a path of at most 3 edges
    vector<int> d(n + 1);
    for (int i = 0; i <= n; ++i) {
        // BFS from vertex i
        queue<int> q;
        q.push(i);
        fill(d.begin(), d.end(), -1);
        d[i] = 0;

        while (!q.empty()) {
            int x = q.front();
            q.pop();

            // All edges are forward: true for the initial chain, and preserved
            // when composing a->b and b->c. Scan only existing edges instead of
            // every possible destination on every BFS (cubic at n=4096).
            for (int v : outgoing[x]) {
                if (d[v] == -1) {
                    d[v] = d[x] + 1;
                    q.push(v);
                }
            }
        }

        // Check distances to all vertices j > i
        for (int j = i + 1; j <= n; ++j) {
            if (d[j] == -1 || d[j] > 3) {
                quitf(_wa, "Distance from vertex %d to vertex %d is %d (expected at most 3)", i, j, d[j] == -1 ? -1 : d[j]);
            }
        }
    }

    // A zero-edge reference is an exact optimum: no improvement is possible.
    double score_ratio;
    if (mans == 0) {
        score_ratio = (mout == 0 ? 1.0 : 0.0);
    } else {
        double normalized_performance = max(0.0, (3.0 * mans - mout) / (2.0 * mans));
        score_ratio = referenceScore(normalized_performance);
    }
    score_ratio = natural_log_score(100.0L * (score_ratio), mout, mans, true) / 100.0;
    double unbounded_ratio = score_ratio;

    quitp(score_ratio, "Value: %d. Ratio: %.12f, RatioUnbounded: %.12f", mout, score_ratio, unbounded_ratio);

    return 0;
}
